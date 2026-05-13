from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from node_service.node_state import STATE
from node_service.routes.admin_routes import router as admin_router
from node_service.routes.raft_routes import router as raft_router
from node_service.routes.paxos_routes import router as paxos_router
from node_service.routes.zab_routes import router as zab_router

app = FastAPI(title=f"Consensus Node {STATE.node_id}", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(raft_router)
app.include_router(paxos_router)
app.include_router(zab_router)


@app.get("/")
def root():
    return {"service": "consensus-node", "node_id": STATE.node_id, "status_url": "/admin/status"}
