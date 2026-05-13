from __future__ import annotations

import os
import time
from copy import deepcopy
from typing import Any, Dict, List, Optional


def parse_peers(raw: str) -> Dict[str, str]:
    peers: Dict[str, str] = {}
    if not raw:
        return peers
    for item in raw.split(","):
        if not item.strip():
            continue
        node_id, url = item.split("=", 1)
        peers[node_id.strip()] = url.strip().rstrip("/")
    return peers


class NodeState:
    """In-memory state for one educational consensus node.

    This project intentionally keeps state in memory so the protocol flow is
    easy to inspect and reset. The node still runs as a real independent HTTP
    service/container and communicates with other nodes through HTTP.
    """

    def __init__(self) -> None:
        self.node_id = os.getenv("NODE_ID", "N1")
        self.port = int(os.getenv("NODE_PORT", "8001"))
        self.peers = parse_peers(os.getenv("PEERS", ""))
        self.alive = True
        self.trace: List[Dict[str, Any]] = []
        self.reset_protocol_state()

    def reset_protocol_state(self) -> None:
        self.kv: Dict[str, str] = {}
        self.applied: List[str] = []

        # Raft
        self.raft_role = "follower"
        self.raft_term = 0
        self.raft_voted_for: Optional[str] = None
        self.raft_leader_id: Optional[str] = None
        self.raft_log: List[Dict[str, Any]] = []
        self.raft_commit_index = 0
        self.raft_last_applied = 0

        # Paxos
        self.paxos_promised_number = 0
        self.paxos_accepted_number = 0
        self.paxos_accepted_value: Optional[str] = None
        self.paxos_learned: List[Dict[str, Any]] = []
        self.paxos_next_proposal = int(time.time() * 1000) % 1_000_000

        # Zab
        self.zab_role = "follower"
        self.zab_epoch = 0
        self.zab_primary_id: Optional[str] = None
        self.zab_log: List[Dict[str, Any]] = []
        self.zab_delivered_zxid = 0

    @property
    def cluster_size(self) -> int:
        return len(self.peers) + 1

    @property
    def quorum(self) -> int:
        return self.cluster_size // 2 + 1

    def event(self, algorithm: str, message: str, kind: str = "info", **extra: Any) -> Dict[str, Any]:
        item = {
            "time": round(time.time(), 3),
            "node": self.node_id,
            "algorithm": algorithm,
            "kind": kind,
            "message": message,
            **extra,
        }
        self.trace.append(item)
        self.trace = self.trace[-300:]
        return item

    def last_raft_index(self) -> int:
        return len(self.raft_log)

    def last_raft_term(self) -> int:
        if not self.raft_log:
            return 0
        return int(self.raft_log[-1]["term"])

    def apply_command(self, value: str) -> None:
        # Supports strings such as: "set x = 100". Other values are appended.
        value = value.strip()
        if value.lower().startswith("set ") and "=" in value:
            left, right = value[4:].split("=", 1)
            self.kv[left.strip()] = right.strip()
        self.applied.append(value)

    def apply_raft_commits(self) -> None:
        while self.raft_last_applied < self.raft_commit_index:
            entry = self.raft_log[self.raft_last_applied]
            if not entry.get("applied"):
                self.apply_command(entry["value"])
                entry["applied"] = True
            self.raft_last_applied += 1

    def status(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "alive": self.alive,
            "peers": self.peers,
            "quorum": self.quorum,
            "kv": deepcopy(self.kv),
            "applied": deepcopy(self.applied),
            "raft": {
                "role": self.raft_role,
                "term": self.raft_term,
                "voted_for": self.raft_voted_for,
                "leader_id": self.raft_leader_id,
                "commit_index": self.raft_commit_index,
                "last_applied": self.raft_last_applied,
                "log": deepcopy(self.raft_log),
            },
            "paxos": {
                "promised_number": self.paxos_promised_number,
                "accepted_number": self.paxos_accepted_number,
                "accepted_value": self.paxos_accepted_value,
                "learned": deepcopy(self.paxos_learned),
            },
            "zab": {
                "role": self.zab_role,
                "epoch": self.zab_epoch,
                "primary_id": self.zab_primary_id,
                "delivered_zxid": self.zab_delivered_zxid,
                "log": deepcopy(self.zab_log),
            },
            "trace": deepcopy(self.trace[-120:]),
        }


STATE = NodeState()
