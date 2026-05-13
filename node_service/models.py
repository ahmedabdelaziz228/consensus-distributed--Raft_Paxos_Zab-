from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClientRequest(BaseModel):
    value: str = Field(..., examples=["set x = 100"])


class RequestVote(BaseModel):
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


class RequestVoteResponse(BaseModel):
    term: int
    vote_granted: bool
    reason: str


class AppendEntries(BaseModel):
    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: List[Dict[str, Any]] = []
    leader_commit: int


class AppendEntriesResponse(BaseModel):
    term: int
    success: bool
    reason: str
    match_index: int = 0


class PaxosPrepare(BaseModel):
    proposal_number: int
    proposer_id: str


class PaxosPromise(BaseModel):
    promised: bool
    promised_number: int
    accepted_number: int
    accepted_value: Optional[str] = None
    reason: str


class PaxosAccept(BaseModel):
    proposal_number: int
    value: str
    proposer_id: str


class PaxosAccepted(BaseModel):
    accepted: bool
    accepted_number: int
    accepted_value: Optional[str]
    reason: str


class PaxosLearn(BaseModel):
    proposal_number: int
    value: str


class ZabDiscoveryInfo(BaseModel):
    node_id: str
    epoch: int
    last_zxid: int
    log: List[Dict[str, Any]]


class ZabSync(BaseModel):
    epoch: int
    primary_id: str
    log: List[Dict[str, Any]]


class ZabPropose(BaseModel):
    epoch: int
    zxid: int
    value: str
    primary_id: str


class ZabAck(BaseModel):
    ack: bool
    zxid: int
    reason: str


class ZabCommit(BaseModel):
    zxid: int
