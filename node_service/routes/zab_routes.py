from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from node_service.models import ClientRequest, ZabAck, ZabCommit, ZabDiscoveryInfo, ZabPropose, ZabSync
from node_service.node_state import STATE
from node_service.utils.http_client import get_json, post_json

router = APIRouter(prefix="/zab", tags=["zab"])


def ensure_alive() -> None:
    if not STATE.alive:
        raise HTTPException(status_code=503, detail=f"{STATE.node_id} is failed")


def last_zxid() -> int:
    if not STATE.zab_log:
        return 0
    return int(STATE.zab_log[-1]["zxid"])


def local_discovery_info() -> ZabDiscoveryInfo:
    return ZabDiscoveryInfo(node_id=STATE.node_id, epoch=STATE.zab_epoch, last_zxid=last_zxid(), log=deepcopy(STATE.zab_log))


@router.get("/discovery-info", response_model=ZabDiscoveryInfo)
def discovery_info():
    ensure_alive()
    info = local_discovery_info()
    STATE.event("zab", f"Discovery info requested: epoch={info.epoch}, last_zxid={info.last_zxid}", "discovery")
    return info


@router.post("/sync")
def sync(payload: ZabSync):
    ensure_alive()
    if payload.epoch >= STATE.zab_epoch:
        STATE.zab_epoch = payload.epoch
        STATE.zab_primary_id = payload.primary_id
        STATE.zab_role = "primary" if payload.primary_id == STATE.node_id else "follower"
        STATE.zab_log = deepcopy(payload.log)
        for entry in STATE.zab_log:
            if entry.get("committed") and not entry.get("applied"):
                STATE.apply_command(entry["value"])
                entry["applied"] = True
                STATE.zab_delivered_zxid = max(STATE.zab_delivered_zxid, int(entry["zxid"]))
        STATE.event("zab", f"Synchronized with primary {payload.primary_id} for epoch {payload.epoch}", "sync")
        return {"synced": True, "node": STATE.node_id, "epoch": STATE.zab_epoch, "role": STATE.zab_role}
    return {"synced": False, "reason": "stale epoch", "node": STATE.node_id, "epoch": STATE.zab_epoch}


@router.post("/recover-cluster")
async def recover_cluster():
    ensure_alive()
    STATE.event("zab", "Starting Zab recovery: Discovery phase", "discovery")
    infos: List[Dict[str, Any]] = [local_discovery_info().model_dump()]

    async def ask(peer_id: str, base_url: str):
        response = await get_json(f"{base_url}/zab/discovery-info")
        return peer_id, response

    responses = await asyncio.gather(*(ask(pid, url) for pid, url in STATE.peers.items()))
    for peer_id, response in responses:
        if response and not response.get("error"):
            infos.append(response)
        else:
            STATE.event("zab", f"Discovery skipped {peer_id}: unavailable", "discovery")

    if len(infos) < STATE.quorum:
        return {"algorithm": "zab", "recovered": False, "reason": "no quorum for discovery", "infos": infos, "quorum": STATE.quorum}

    freshest = sorted(infos, key=lambda x: (int(x["epoch"]), int(x["last_zxid"]), x["node_id"]), reverse=True)[0]
    new_epoch = max(int(info["epoch"]) for info in infos) + 1
    selected_log = freshest.get("log", [])

    # This endpoint acts as the new primary after proving it saw a quorum.
    STATE.zab_epoch = new_epoch
    STATE.zab_role = "primary"
    STATE.zab_primary_id = STATE.node_id
    STATE.zab_log = deepcopy(selected_log)
    STATE.event("zab", f"Elected {STATE.node_id} as primary for epoch {new_epoch}; freshest history from {freshest['node_id']}", "election")

    sync_payload = ZabSync(epoch=new_epoch, primary_id=STATE.node_id, log=STATE.zab_log)
    sync_results: List[Dict[str, Any]] = [{"node": STATE.node_id, "response": {"synced": True}}]

    async def send_sync(peer_id: str, base_url: str):
        response = await post_json(f"{base_url}/zab/sync", sync_payload.model_dump())
        return {"node": peer_id, "response": response}

    sync_results.extend(await asyncio.gather(*(send_sync(pid, url) for pid, url in STATE.peers.items())))
    synced_count = len([s for s in sync_results if s["response"] and s["response"].get("synced")])
    recovered = synced_count >= STATE.quorum
    if recovered:
        STATE.event("zab", f"Synchronization quorum reached: synced={synced_count}/{STATE.quorum}", "sync")
    return {
        "algorithm": "zab",
        "recovered": recovered,
        "primary": STATE.node_id,
        "epoch": new_epoch,
        "discovery": infos,
        "sync_results": sync_results,
        "quorum": STATE.quorum,
        "status": STATE.status(),
    }


@router.post("/propose", response_model=ZabAck)
def propose(payload: ZabPropose):
    ensure_alive()
    if payload.epoch < STATE.zab_epoch:
        return ZabAck(ack=False, zxid=payload.zxid, reason="stale epoch")
    STATE.zab_epoch = payload.epoch
    STATE.zab_primary_id = payload.primary_id
    STATE.zab_role = "follower"
    if not any(int(e["zxid"]) == payload.zxid for e in STATE.zab_log):
        STATE.zab_log.append({"zxid": payload.zxid, "epoch": payload.epoch, "value": payload.value, "committed": False, "applied": False})
    STATE.event("zab", f"Accepted PROPOSE zxid={payload.zxid}, value={payload.value}", "propose")
    return ZabAck(ack=True, zxid=payload.zxid, reason="proposal accepted")


@router.post("/commit")
def commit(payload: ZabCommit):
    ensure_alive()
    for entry in STATE.zab_log:
        if int(entry["zxid"]) == payload.zxid:
            entry["committed"] = True
            if not entry.get("applied"):
                STATE.apply_command(entry["value"])
                entry["applied"] = True
            STATE.zab_delivered_zxid = max(STATE.zab_delivered_zxid, payload.zxid)
            STATE.event("zab", f"Committed and delivered zxid={payload.zxid}", "commit")
            return {"committed": True, "node": STATE.node_id, "zxid": payload.zxid}
    return {"committed": False, "node": STATE.node_id, "reason": "zxid not found"}


@router.post("/client-request")
async def client_request(payload: ClientRequest):
    ensure_alive()
    if STATE.zab_role != "primary":
        raise HTTPException(status_code=409, detail=f"{STATE.node_id} is not Zab primary")

    zxid = (STATE.zab_epoch << 32) + (last_zxid() & 0xFFFFFFFF) + 1
    entry = {"zxid": zxid, "epoch": STATE.zab_epoch, "value": payload.value, "committed": False, "applied": False}
    STATE.zab_log.append(entry)
    STATE.event("zab", f"Primary proposes zxid={zxid}, value={payload.value}", "propose")

    propose_payload = ZabPropose(epoch=STATE.zab_epoch, zxid=zxid, value=payload.value, primary_id=STATE.node_id)

    async def send_propose(peer_id: str, base_url: str):
        response = await post_json(f"{base_url}/zab/propose", propose_payload.model_dump())
        return {"node": peer_id, "response": response}

    propose_results = await asyncio.gather(*(send_propose(pid, url) for pid, url in STATE.peers.items()))
    ack_count = 1 + len([p for p in propose_results if p["response"] and p["response"].get("ack")])
    committed = ack_count >= STATE.quorum
    commit_results: List[Dict[str, Any]] = []
    if committed:
        entry["committed"] = True
        if not entry.get("applied"):
            STATE.apply_command(entry["value"])
            entry["applied"] = True
        STATE.zab_delivered_zxid = zxid
        STATE.event("zab", f"zxid={zxid} reached quorum ACK and is committed", "commit")
        commit_payload = ZabCommit(zxid=zxid)

        async def send_commit(peer_id: str, base_url: str):
            response = await post_json(f"{base_url}/zab/commit", commit_payload.model_dump())
            return {"node": peer_id, "response": response}

        commit_results = await asyncio.gather(*(send_commit(pid, url) for pid, url in STATE.peers.items()))

    return {
        "algorithm": "zab",
        "primary": STATE.node_id,
        "epoch": STATE.zab_epoch,
        "zxid": zxid,
        "value": payload.value,
        "acks": ack_count,
        "quorum": STATE.quorum,
        "committed": committed,
        "propose_results": propose_results,
        "commit_results": commit_results,
        "status": STATE.status(),
    }
