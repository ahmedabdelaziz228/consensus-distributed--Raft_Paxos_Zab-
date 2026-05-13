from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import httpx


def parse_nodes(raw: str) -> Dict[str, str]:
    nodes: Dict[str, str] = {}
    for item in raw.split(","):
        if not item.strip():
            continue
        node_id, url = item.split("=", 1)
        nodes[node_id.strip()] = url.strip().rstrip("/")
    return nodes


NODES = parse_nodes(os.getenv("CLUSTER_NODES", "N1=http://localhost:8001,N2=http://localhost:8002,N3=http://localhost:8003,N4=http://localhost:8004,N5=http://localhost:8005"))


async def get_json(url: str, timeout: float = 3.0) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        return {"error": str(exc)}


async def post_json(url: str, payload: Dict[str, Any] | None = None, timeout: float = 8.0) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload or {})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        try:
            body = exc.response.json()
        except Exception:
            body = exc.response.text
        return {"error": f"HTTP {exc.response.status_code}", "detail": body}
    except Exception as exc:
        return {"error": str(exc)}


async def collect_status() -> Dict[str, Any]:
    statuses: Dict[str, Any] = {}
    for node_id, base_url in NODES.items():
        statuses[node_id] = await get_json(f"{base_url}/admin/status")
    traces: List[Dict[str, Any]] = []
    for node_id, status in statuses.items():
        if isinstance(status, dict) and not status.get("error"):
            traces.extend(status.get("trace", []))
    traces.sort(key=lambda e: e.get("time", 0))
    return {"nodes": statuses, "trace": traces[-250:]}


async def first_alive_node() -> Optional[tuple[str, str]]:
    for node_id, base_url in NODES.items():
        status = await get_json(f"{base_url}/admin/status")
        if status.get("alive"):
            return node_id, base_url
    return None


async def find_raft_leader() -> Optional[tuple[str, str]]:
    for node_id, base_url in NODES.items():
        status = await get_json(f"{base_url}/admin/status")
        if status.get("alive") and status.get("raft", {}).get("role") == "leader":
            return node_id, base_url
    return None


async def find_zab_primary() -> Optional[tuple[str, str]]:
    for node_id, base_url in NODES.items():
        status = await get_json(f"{base_url}/admin/status")
        if status.get("alive") and status.get("zab", {}).get("role") == "primary":
            return node_id, base_url
    return None
