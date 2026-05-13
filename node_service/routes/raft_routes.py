from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from node_service.models import AppendEntries, AppendEntriesResponse, ClientRequest, RequestVote, RequestVoteResponse
from node_service.node_state import STATE
from node_service.utils.http_client import post_json

router = APIRouter(prefix="/raft", tags=["raft"])


def ensure_alive() -> None:
    if not STATE.alive:
        raise HTTPException(status_code=503, detail=f"{STATE.node_id} is failed")


def is_candidate_log_up_to_date(last_log_index: int, last_log_term: int) -> bool:
    my_last_term = STATE.last_raft_term()
    my_last_index = STATE.last_raft_index()
    return (last_log_term > my_last_term) or (
        last_log_term == my_last_term and last_log_index >= my_last_index
    )


@router.post("/request-vote", response_model=RequestVoteResponse)
def request_vote(payload: RequestVote):
    ensure_alive()
    if payload.term > STATE.raft_term:
        STATE.raft_term = payload.term
        STATE.raft_voted_for = None
        STATE.raft_role = "follower"
        STATE.raft_leader_id = None

    if payload.term < STATE.raft_term:
        STATE.event("raft", f"Rejected vote for {payload.candidate_id}: stale term {payload.term}", "vote")
        return RequestVoteResponse(term=STATE.raft_term, vote_granted=False, reason="stale term")

    up_to_date = is_candidate_log_up_to_date(payload.last_log_index, payload.last_log_term)
    can_vote = STATE.raft_voted_for in (None, payload.candidate_id)
    granted = can_vote and up_to_date
    if granted:
        STATE.raft_voted_for = payload.candidate_id
        STATE.event("raft", f"Granted vote to {payload.candidate_id} for term {payload.term}", "vote")
        return RequestVoteResponse(term=STATE.raft_term, vote_granted=True, reason="vote granted")

    reason = "already voted" if not can_vote else "candidate log is stale"
    STATE.event("raft", f"Rejected vote for {payload.candidate_id}: {reason}", "vote")
    return RequestVoteResponse(term=STATE.raft_term, vote_granted=False, reason=reason)


@router.post("/append-entries", response_model=AppendEntriesResponse)
def append_entries(payload: AppendEntries):
    ensure_alive()
    if payload.term < STATE.raft_term:
        return AppendEntriesResponse(term=STATE.raft_term, success=False, reason="stale leader term")

    if payload.term >= STATE.raft_term:
        STATE.raft_term = payload.term
        STATE.raft_role = "follower"
        STATE.raft_leader_id = payload.leader_id
        STATE.raft_voted_for = None

    if payload.prev_log_index > 0:
        if len(STATE.raft_log) < payload.prev_log_index:
            STATE.event("raft", f"Rejected AppendEntries from {payload.leader_id}: missing prevLogIndex", "append")
            return AppendEntriesResponse(term=STATE.raft_term, success=False, reason="missing previous index")
        prev_entry = STATE.raft_log[payload.prev_log_index - 1]
        if int(prev_entry["term"]) != payload.prev_log_term:
            STATE.raft_log = STATE.raft_log[: payload.prev_log_index - 1]
            STATE.event("raft", f"Rejected AppendEntries from {payload.leader_id}: term conflict", "append")
            return AppendEntriesResponse(term=STATE.raft_term, success=False, reason="previous term mismatch")

    for entry in payload.entries:
        index = int(entry["index"])
        if len(STATE.raft_log) >= index:
            existing = STATE.raft_log[index - 1]
            if existing["term"] != entry["term"] or existing["value"] != entry["value"]:
                STATE.raft_log = STATE.raft_log[: index - 1]
        if len(STATE.raft_log) < index:
            new_entry = dict(entry)
            new_entry.setdefault("committed", False)
            new_entry.setdefault("applied", False)
            STATE.raft_log.append(new_entry)
            STATE.event("raft", f"Appended entry #{index}: {new_entry['value']}", "append")

    if payload.leader_commit > STATE.raft_commit_index:
        STATE.raft_commit_index = min(payload.leader_commit, len(STATE.raft_log))
        for i in range(STATE.raft_commit_index):
            STATE.raft_log[i]["committed"] = True
        STATE.apply_raft_commits()
        STATE.event("raft", f"Updated commit index to {STATE.raft_commit_index}", "commit")

    return AppendEntriesResponse(
        term=STATE.raft_term,
        success=True,
        reason="append successful",
        match_index=len(STATE.raft_log),
    )


@router.post("/start-election")
async def start_election():
    ensure_alive()
    STATE.raft_role = "candidate"
    STATE.raft_term += 1
    STATE.raft_voted_for = STATE.node_id
    STATE.raft_leader_id = None
    votes = 1
    STATE.event("raft", f"{STATE.node_id} starts election for term {STATE.raft_term}", "election")

    payload = RequestVote(
        term=STATE.raft_term,
        candidate_id=STATE.node_id,
        last_log_index=STATE.last_raft_index(),
        last_log_term=STATE.last_raft_term(),
    ).model_dump()

    async def ask(peer_id: str, base_url: str):
        return peer_id, await post_json(f"{base_url}/raft/request-vote", payload)

    results = await asyncio.gather(*(ask(pid, url) for pid, url in STATE.peers.items()))
    responses: List[Dict[str, Any]] = []
    for peer_id, response in results:
        responses.append({"peer": peer_id, "response": response})
        if response and response.get("vote_granted"):
            votes += 1
            STATE.event("raft", f"Received vote from {peer_id}. votes={votes}/{STATE.quorum}", "election")
        elif response and response.get("term", 0) > STATE.raft_term:
            STATE.raft_term = response["term"]
            STATE.raft_role = "follower"
            STATE.raft_voted_for = None

    elected = votes >= STATE.quorum
    if elected:
        STATE.raft_role = "leader"
        STATE.raft_leader_id = STATE.node_id
        STATE.event("raft", f"{STATE.node_id} became leader for term {STATE.raft_term}", "election")
        await send_heartbeats()
    else:
        STATE.raft_role = "follower"
        STATE.event("raft", f"Election failed. votes={votes}/{STATE.quorum}", "election")

    return {"elected": elected, "votes": votes, "quorum": STATE.quorum, "responses": responses, "status": STATE.status()}


async def send_heartbeats() -> List[Dict[str, Any]]:
    payload = AppendEntries(
        term=STATE.raft_term,
        leader_id=STATE.node_id,
        prev_log_index=STATE.last_raft_index(),
        prev_log_term=STATE.last_raft_term(),
        entries=[],
        leader_commit=STATE.raft_commit_index,
    ).model_dump()

    async def send(peer_id: str, base_url: str):
        return {"peer": peer_id, "response": await post_json(f"{base_url}/raft/append-entries", payload)}

    return await asyncio.gather(*(send(pid, url) for pid, url in STATE.peers.items()))


@router.post("/client-request")
async def client_request(payload: ClientRequest):
    ensure_alive()
    if STATE.raft_role != "leader":
        raise HTTPException(status_code=409, detail=f"{STATE.node_id} is not Raft leader")

    index = STATE.last_raft_index() + 1
    prev_log_index = index - 1
    prev_log_term = STATE.raft_log[prev_log_index - 1]["term"] if prev_log_index > 0 else 0
    entry = {"index": index, "term": STATE.raft_term, "value": payload.value, "committed": False, "applied": False}
    STATE.raft_log.append(entry)
    STATE.event("raft", f"Leader appended client command as log entry #{index}: {payload.value}", "client")

    ae = AppendEntries(
        term=STATE.raft_term,
        leader_id=STATE.node_id,
        prev_log_index=prev_log_index,
        prev_log_term=prev_log_term,
        entries=[entry],
        leader_commit=STATE.raft_commit_index,
    ).model_dump()

    async def replicate(peer_id: str, base_url: str):
        response = await post_json(f"{base_url}/raft/append-entries", ae)
        return peer_id, response

    results = await asyncio.gather(*(replicate(pid, url) for pid, url in STATE.peers.items()))
    acknowledgements = 1
    peer_results: List[Dict[str, Any]] = []
    for peer_id, response in results:
        peer_results.append({"peer": peer_id, "response": response})
        if response and response.get("success"):
            acknowledgements += 1
            STATE.event("raft", f"Follower {peer_id} acknowledged entry #{index}. acks={acknowledgements}/{STATE.quorum}", "ack")

    committed = acknowledgements >= STATE.quorum
    if committed:
        STATE.raft_commit_index = index
        STATE.raft_log[index - 1]["committed"] = True
        STATE.apply_raft_commits()
        STATE.event("raft", f"Entry #{index} committed by majority and applied", "commit")
        await send_heartbeats()

    return {
        "algorithm": "raft",
        "leader": STATE.node_id,
        "value": payload.value,
        "acks": acknowledgements,
        "quorum": STATE.quorum,
        "committed": committed,
        "replication": peer_results,
        "status": STATE.status(),
    }
