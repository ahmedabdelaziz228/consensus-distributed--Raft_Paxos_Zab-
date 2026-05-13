# Algorithms Explanation

## Raft

Raft is a leader-based replicated log protocol. The key idea is that one leader receives client commands and replicates log entries to followers.

Implemented steps:

- RequestVote
- VoteGranted
- AppendEntries
- Majority ACK
- Commit
- Apply to state machine

## Paxos

Paxos reaches agreement on a value through two main phases.

Implemented steps:

- Prepare
- Promise
- Accept
- Accepted
- Learn

## Zab

Zab is a primary-backup atomic broadcast protocol used by ZooKeeper.

Implemented steps:

- Discovery
- Synchronization
- Broadcast
- PROPOSE
- ACK
- COMMIT
