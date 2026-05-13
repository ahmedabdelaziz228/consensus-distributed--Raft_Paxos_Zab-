# Report Notes

Use this project as the practical implementation part of a distributed systems report.

## What to mention

- The system uses 5 nodes.
- Each node runs as an independent service.
- Nodes communicate through HTTP.
- Quorum is 3 out of 5.
- Raft uses leader election and log replication.
- Paxos uses prepare/promise and accept/accepted.
- Zab uses discovery, synchronization, and broadcast.
- Node failure is simulated by making a node stop responding to protocol endpoints.

## Limitations

- State is in memory, not persisted to disk.
- Network partitions are not fully simulated.
- Timing and randomized elections are simplified.
- The project is educational, not production-grade.
