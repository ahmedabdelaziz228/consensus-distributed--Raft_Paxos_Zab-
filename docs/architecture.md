# Architecture

The system contains a gateway and five node services.

## Gateway

The gateway exposes a user-facing API and serves the dashboard. It does not implement the consensus protocols directly. Instead, it forwards client requests to one of the node services.

## Node services

Each node is a FastAPI service with its own in-memory state. Nodes communicate through HTTP endpoints.

## Why HTTP?

HTTP makes the message exchange visible, easy to debug, and easy to demonstrate. In a production system, consensus nodes might use gRPC, TCP, or a custom RPC layer.

## Quorum

With five nodes, quorum is three nodes:

```text
quorum = floor(5 / 2) + 1 = 3
```

Any decision must be accepted by at least three nodes.
