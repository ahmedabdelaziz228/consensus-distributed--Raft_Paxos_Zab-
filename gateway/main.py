from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from gateway.cluster_client import NODES, collect_status, find_raft_leader, find_zab_primary, first_alive_node, post_json


class RequestPayload(BaseModel):
    value: str


app = FastAPI(title="Consensus Distributed Lab Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="gateway/dashboard"), name="static")


@app.get("/")
def dashboard():
    return FileResponse("gateway/dashboard/index.html")


@app.get("/api/status")
async def api_status():
    return await collect_status()


@app.post("/api/reset")
async def reset_all():
    results = {}
    for node_id, base_url in NODES.items():
        results[node_id] = await post_json(f"{base_url}/admin/reset")
    return {"ok": True, "results": results, "cluster": await collect_status()}


@app.post("/api/nodes/{node_id}/fail")
async def fail_node(node_id: str):
    base_url = NODES.get(node_id.upper())
    if not base_url:
        raise HTTPException(status_code=404, detail="node not found")
    result = await post_json(f"{base_url}/admin/fail")
    return {"node": node_id.upper(), "result": result, "cluster": await collect_status()}


@app.post("/api/nodes/{node_id}/recover")
async def recover_node(node_id: str):
    base_url = NODES.get(node_id.upper())
    if not base_url:
        raise HTTPException(status_code=404, detail="node not found")
    result = await post_json(f"{base_url}/admin/recover")
    return {"node": node_id.upper(), "result": result, "cluster": await collect_status()}


@app.post("/api/raft/elect")
async def raft_elect():
    candidate = await first_alive_node()
    if not candidate:
        raise HTTPException(status_code=503, detail="no alive nodes")
    node_id, base_url = candidate
    result = await post_json(f"{base_url}/raft/start-election")
    return {"candidate": node_id, "result": result, "cluster": await collect_status()}


@app.post("/api/raft/request")
async def raft_request(payload: RequestPayload):
    leader = await find_raft_leader()
    if not leader:
        election = await raft_elect()
        leader = await find_raft_leader()
        if not leader:
            return {"error": "Raft leader election failed", "election": election, "cluster": await collect_status()}
    node_id, base_url = leader
    result = await post_json(f"{base_url}/raft/client-request", payload.model_dump())
    return {"leader": node_id, "result": result, "cluster": await collect_status()}


@app.post("/api/paxos/request")
async def paxos_request(payload: RequestPayload):
    proposer = await first_alive_node()
    if not proposer:
        raise HTTPException(status_code=503, detail="no alive nodes")
    node_id, base_url = proposer
    result = await post_json(f"{base_url}/paxos/propose", payload.model_dump())
    return {"proposer": node_id, "result": result, "cluster": await collect_status()}


@app.post("/api/zab/recover")
async def zab_recover():
    candidate = await first_alive_node()
    if not candidate:
        raise HTTPException(status_code=503, detail="no alive nodes")
    node_id, base_url = candidate
    result = await post_json(f"{base_url}/zab/recover-cluster")
    return {"candidate": node_id, "result": result, "cluster": await collect_status()}


@app.post("/api/zab/request")
async def zab_request(payload: RequestPayload):
    primary = await find_zab_primary()
    if not primary:
        await zab_recover()
        primary = await find_zab_primary()
        if not primary:
            return {"error": "Zab recovery/primary election failed", "cluster": await collect_status()}
    node_id, base_url = primary
    result = await post_json(f"{base_url}/zab/client-request", payload.model_dump())
    return {"primary": node_id, "result": result, "cluster": await collect_status()}
