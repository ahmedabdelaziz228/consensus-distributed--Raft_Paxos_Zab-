from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from node_service.models import ClientRequest, PaxosAccept, PaxosAccepted, PaxosLearn, PaxosPrepare, PaxosPromise
from node_service.node_state import STATE
from node_service.utils.http_client import post_json

router = APIRouter(prefix="/paxos", tags=["paxos"])


def ensure_alive() -> None:
    if not STATE.alive:
        raise HTTPException(status_code=503, detail=f"{STATE.node_id} is failed")


def local_prepare(payload: PaxosPrepare) -> PaxosPromise:
    if payload.proposal_number > STATE.paxos_promised_number:
        STATE.paxos_promised_number = payload.proposal_number
        STATE.event("paxos", f"Promised proposal n={payload.proposal_number} to {payload.proposer_id}", "promise")
        return PaxosPromise(
            promised=True,
            promised_number=STATE.paxos_promised_number,
            accepted_number=STATE.paxos_accepted_number,
            accepted_value=STATE.paxos_accepted_value,
            reason="promise granted",
        )
    return PaxosPromise(
        promised=False,
        promised_number=STATE.paxos_promised_number,
        accepted_number=STATE.paxos_accepted_number,
        accepted_value=STATE.paxos_accepted_value,
        reason="proposal number is not high enough",
    )


def local_accept(payload: PaxosAccept) -> PaxosAccepted:
    if payload.proposal_number >= STATE.paxos_promised_number:
        STATE.paxos_promised_number = payload.proposal_number
        STATE.paxos_accepted_number = payload.proposal_number
        STATE.paxos_accepted_value = payload.value
        STATE.event("paxos", f"Accepted proposal n={payload.proposal_number}, value={payload.value}", "accepted")
        return PaxosAccepted(
            accepted=True,
            accepted_number=STATE.paxos_accepted_number,
            accepted_value=STATE.paxos_accepted_value,
            reason="accepted",
        )
    return PaxosAccepted(
        accepted=False,
        accepted_number=STATE.paxos_accepted_number,
        accepted_value=STATE.paxos_accepted_value,
        reason="proposal number is lower than promised number",
    )


@router.post("/prepare", response_model=PaxosPromise)
def prepare(payload: PaxosPrepare):
    ensure_alive()
    return local_prepare(payload)


@router.post("/accept", response_model=PaxosAccepted)
def accept(payload: PaxosAccept):
    ensure_alive()
    return local_accept(payload)


@router.post("/learn")
def learn(payload: PaxosLearn):
    ensure_alive()
    learned = {"proposal_number": payload.proposal_number, "value": payload.value}
    if learned not in STATE.paxos_learned:
        STATE.paxos_learned.append(learned)
        STATE.apply_command(payload.value)
        STATE.event("paxos", f"Learned chosen value from n={payload.proposal_number}: {payload.value}", "learn")
    return {"learned": True, "node": STATE.node_id, "value": payload.value}


@router.post("/propose")
async def propose(payload: ClientRequest):
    ensure_alive()
    STATE.paxos_next_proposal += STATE.cluster_size
    n = STATE.paxos_next_proposal
    proposer_id = STATE.node_id
    STATE.event("paxos", f"Proposer {proposer_id} starts Paxos round n={n} for value={payload.value}", "prepare")

    prepare_payload = PaxosPrepare(proposal_number=n, proposer_id=proposer_id)
    promises: List[Dict[str, Any]] = []

    local_promise = local_prepare(prepare_payload)
    promises.append({"node": STATE.node_id, "response": local_promise.model_dump()})

    async def send_prepare(peer_id: str, base_url: str):
        response = await post_json(f"{base_url}/paxos/prepare", prepare_payload.model_dump())
        return {"node": peer_id, "response": response}

    promises.extend(await asyncio.gather(*(send_prepare(pid, url) for pid, url in STATE.peers.items())))
    granted = [p for p in promises if p["response"] and p["response"].get("promised")]

    if len(granted) < STATE.quorum:
        STATE.event("paxos", f"Prepare phase failed: promises={len(granted)}/{STATE.quorum}", "prepare")
        return {"algorithm": "paxos", "chosen": False, "phase": "prepare", "promises": promises, "quorum": STATE.quorum}

    chosen_value = payload.value
    highest_accepted = -1
    for item in granted:
        response = item["response"]
        accepted_number = int(response.get("accepted_number") or 0)
        accepted_value = response.get("accepted_value")
        if accepted_value is not None and accepted_number > highest_accepted:
            highest_accepted = accepted_number
            chosen_value = accepted_value

    STATE.event("paxos", f"Prepare quorum reached. Proposer moves to Accept phase with value={chosen_value}", "accept")
    accept_payload = PaxosAccept(proposal_number=n, value=chosen_value, proposer_id=proposer_id)
    accepted: List[Dict[str, Any]] = []
    local_accepted = local_accept(accept_payload)
    accepted.append({"node": STATE.node_id, "response": local_accepted.model_dump()})

    async def send_accept(peer_id: str, base_url: str):
        response = await post_json(f"{base_url}/paxos/accept", accept_payload.model_dump())
        return {"node": peer_id, "response": response}

    accepted.extend(await asyncio.gather(*(send_accept(pid, url) for pid, url in STATE.peers.items())))
    accepted_ok = [a for a in accepted if a["response"] and a["response"].get("accepted")]
    if len(accepted_ok) < STATE.quorum:
        STATE.event("paxos", f"Accept phase failed: accepted={len(accepted_ok)}/{STATE.quorum}", "accept")
        return {"algorithm": "paxos", "chosen": False, "phase": "accept", "promises": promises, "accepted": accepted, "quorum": STATE.quorum}

    STATE.event("paxos", f"Value chosen by majority: {chosen_value}", "chosen")
    learn_payload = PaxosLearn(proposal_number=n, value=chosen_value)
    learn(learn_payload)

    async def send_learn(peer_id: str, base_url: str):
        response = await post_json(f"{base_url}/paxos/learn", learn_payload.model_dump())
        return {"node": peer_id, "response": response}

    learned = await asyncio.gather(*(send_learn(pid, url) for pid, url in STATE.peers.items()))
    return {
        "algorithm": "paxos",
        "proposer": proposer_id,
        "proposal_number": n,
        "chosen": True,
        "value": chosen_value,
        "promises_count": len(granted),
        "accepted_count": len(accepted_ok),
        "quorum": STATE.quorum,
        "promises": promises,
        "accepted": accepted,
        "learned": learned,
        "status": STATE.status(),
    }
