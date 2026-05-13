from __future__ import annotations

from fastapi import APIRouter
from node_service.node_state import STATE

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status")
def status():
    return STATE.status()


@router.post("/fail")
def fail():
    STATE.alive = False
    STATE.raft_role = "failed"
    STATE.zab_role = "failed"
    STATE.event("admin", "Node was marked as failed", "failure")
    return {"ok": True, "node": STATE.node_id, "alive": STATE.alive}


@router.post("/recover")
def recover():
    STATE.alive = True
    if STATE.raft_role == "failed":
        STATE.raft_role = "follower"
    if STATE.zab_role == "failed":
        STATE.zab_role = "follower"
    STATE.event("admin", "Node recovered and can respond again", "recovery")
    return {"ok": True, "node": STATE.node_id, "alive": STATE.alive}


@router.post("/reset")
def reset():
    STATE.alive = True
    STATE.trace.clear()
    STATE.reset_protocol_state()
    STATE.event("admin", "Node state reset", "reset")
    return {"ok": True, "node": STATE.node_id}
