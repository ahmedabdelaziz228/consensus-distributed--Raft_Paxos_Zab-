from __future__ import annotations

from typing import Any, Dict, Optional
import httpx


async def post_json(url: str, payload: Dict[str, Any], timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as exc:  # node failed, network issue, or protocol rejection
        return {"error": str(exc)}


async def get_json(url: str, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        return {"error": str(exc)}
