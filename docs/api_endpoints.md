# API Endpoints

## Gateway

```text
GET  /api/status
POST /api/reset
POST /api/raft/elect
POST /api/raft/request
POST /api/paxos/request
POST /api/zab/recover
POST /api/zab/request
POST /api/nodes/{node_id}/fail
POST /api/nodes/{node_id}/recover
```

## Node Admin

```text
GET  /admin/status
POST /admin/fail
POST /admin/recover
POST /admin/reset
```

## Raft Node API

```text
POST /raft/request-vote
POST /raft/append-entries
POST /raft/start-election
POST /raft/client-request
```

## Paxos Node API

```text
POST /paxos/prepare
POST /paxos/accept
POST /paxos/learn
POST /paxos/propose
```

## Zab Node API

```text
GET  /zab/discovery-info
POST /zab/sync
POST /zab/recover-cluster
POST /zab/propose
POST /zab/commit
POST /zab/client-request
```
