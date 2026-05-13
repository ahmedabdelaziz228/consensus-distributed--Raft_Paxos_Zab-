# Distributed Consensus Algorithms Lab

An educational, hands-on distributed systems project that demonstrates **Distributed Consensus** using three well-known protocols:

- **Raft**
- **Paxos**
- **Zab - ZooKeeper Atomic Broadcast**

This project is not a single-file simulation. It runs **5 independent nodes** inside Docker containers. Each node is a separate FastAPI service, and nodes communicate with each other through real HTTP requests. This makes the consensus flow easier to observe, test, and explain through APIs and a live dashboard.

---

## Table of Contents

- [Project Idea](#project-idea)
- [What This Project Demonstrates](#what-this-project-demonstrates)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [How to Run](#how-to-run)
- [Running Services](#running-services)
- [Dashboard](#dashboard)
- [API Usage](#api-usage)
- [Raft Examples](#raft-examples)
- [Paxos Examples](#paxos-examples)
- [Zab Examples](#zab-examples)
- [Failure and Recovery](#failure-and-recovery)
- [PowerShell Notes](#powershell-notes)
- [How the Algorithms Work](#how-the-algorithms-work)
- [State Machine Commands](#state-machine-commands)
- [Gateway API Reference](#gateway-api-reference)
- [Node Admin API Reference](#node-admin-api-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Suggested Report Description](#suggested-report-description)
- [Suggested LinkedIn / GitHub Summary](#suggested-linkedin--github-summary)
- [Author Notes](#author-notes)

---

## Project Idea

In distributed systems, multiple servers or nodes often need to agree on the same value or decision, even if some nodes fail or network communication is delayed.

This agreement process is called **consensus**.

This project demonstrates consensus practically using a cluster of 5 nodes. Each node has its own internal state and communicates with the other nodes through HTTP. When a command such as the following is submitted:

```text
set x = 100
```

The selected consensus protocol attempts to reach agreement among a majority of the nodes. Once agreement is reached, the command is applied to a replicated state machine.

---

## What This Project Demonstrates

This project demonstrates important distributed systems concepts, including:

- Running multiple nodes as independent services.
- Quorum-based decision making.
- Majority voting.
- Leader election in Raft.
- Log replication in Raft.
- Prepare, Promise, Accept, and Learn phases in Paxos.
- Primary election and atomic broadcast in Zab.
- Node failure simulation.
- Node recovery simulation.
- Protocol trace logging.
- A simple replicated key-value state machine.

---

## Architecture

```text
                         +----------------------+
                         | Gateway + Dashboard  |
                         | http://localhost:8000|
                         +----------+-----------+
                                    |
              +---------------------+---------------------+
              |                     |                     |
       +------v------+       +------v------+       +------v------+
       |    Node 1   |       |    Node 2   |       |    Node 3   |
       | localhost:8001      | localhost:8002      | localhost:8003
       +-------------+       +-------------+       +-------------+
              |                     |                     |
       +------v------+       +------v------+
       |    Node 4   |       |    Node 5   |
       | localhost:8004      | localhost:8005
       +-------------+       +-------------+
```

### Main Components

#### 1. Gateway

The gateway is the main entry point for the user. It is responsible for:

- Serving the dashboard.
- Receiving user API requests.
- Detecting or triggering the Raft leader.
- Detecting or triggering the Zab primary.
- Forwarding client requests to the appropriate node.
- Collecting status information from all nodes.
- Providing unified APIs for fail, recover, and reset operations.

The gateway runs on:

```text
http://localhost:8000
```

#### 2. Node Services

Each node is an independent FastAPI service. Every node has:

- A node ID, such as `N1`, `N2`, etc.
- A list of peer nodes.
- In-memory state.
- Raft state.
- Paxos state.
- Zab state.
- A trace log for protocol events.

#### 3. Dashboard

The project includes a simple HTML, CSS, and JavaScript dashboard that allows users to visually observe the cluster state, protocol logs, node failures, recoveries, and state machine values.

---

## Tech Stack

- **Python 3.11**
- **FastAPI**
- **Uvicorn**
- **HTTPX**
- **Pydantic**
- **Docker**
- **Docker Compose**
- **HTML / CSS / JavaScript**
- **Pytest**

---

## Project Structure

```text
consensus-distributed-lab/
|
|-- gateway/
|   |-- main.py                   # Gateway API + dashboard server
|   |-- cluster_client.py          # Helper functions for node communication
|   |-- dashboard/
|       |-- index.html             # Dashboard page
|       |-- style.css              # Dashboard styles
|       |-- app.js                 # Dashboard client-side logic
|
|-- node_service/
|   |-- main.py                   # FastAPI app for each node
|   |-- node_state.py              # In-memory node state
|   |-- models.py                  # Pydantic request/response models
|   |-- routes/
|   |   |-- admin_routes.py         # status, fail, recover, reset
|   |   |-- raft_routes.py          # Raft endpoints
|   |   |-- paxos_routes.py         # Paxos endpoints
|   |   |-- zab_routes.py           # Zab endpoints
|   |-- utils/
|       |-- http_client.py          # HTTP helper functions
|
|-- docs/
|   |-- architecture.md
|   |-- algorithms_explanation.md
|   |-- api_endpoints.md
|   |-- report_notes.md
|
|-- tests/
|   |-- test_quorum.py
|
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
|-- README.md
|-- .gitignore
```

---

## Requirements

Before running the project, make sure you have:

- Docker Desktop
- Docker Compose
- A terminal such as PowerShell, CMD, Git Bash, Linux Terminal, or macOS Terminal

You do **not** need to install Python locally if you run the project using Docker.

---

## How to Run

### 1. Open a terminal inside the project folder

Example on Windows:

```powershell
cd "C:\Users\lap shop\Downloads\consensus-distributed-lab-python\consensus-distributed-lab"
```

### 2. Start the project

```bash
docker compose up --build
```

If your Docker installation uses the old Compose command, use:

```bash
docker-compose up --build
```

### 3. Open the dashboard

Open your browser and go to:

```text
http://localhost:8000
```

### 4. Stop the project

In the same terminal, press:

```text
Ctrl + C
```

Then run:

```bash
docker compose down
```

---

## Running Services

After starting the project, the services will be available at:

| Service | URL | Description |
|---|---|---|
| Gateway | `http://localhost:8000` | Dashboard + public API |
| Node 1 | `http://localhost:8001` | Consensus node N1 |
| Node 2 | `http://localhost:8002` | Consensus node N2 |
| Node 3 | `http://localhost:8003` | Consensus node N3 |
| Node 4 | `http://localhost:8004` | Consensus node N4 |
| Node 5 | `http://localhost:8005` | Consensus node N5 |

---

## Dashboard

After opening:

```text
http://localhost:8000
```

You can monitor:

- The status of each node.
- Whether each node is alive or failed.
- The Raft role of each node.
- The Zab role of each node.
- Protocol logs.
- The key-value state produced by committed commands.
- Election, commit, replication, failure, and recovery events.

---

## API Usage

### Get Cluster Status

#### PowerShell

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/status" -Method GET
```

#### curl / Git Bash / Linux / macOS

```bash
curl http://localhost:8000/api/status
```

This endpoint returns the status of all nodes and their protocol trace events.

---

### Reset Cluster

This resets all nodes back to the initial state.

#### PowerShell

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/reset" -Method POST
```

#### curl / Git Bash / Linux / macOS

```bash
curl -X POST http://localhost:8000/api/reset
```

---

## Raft Examples

### Start Raft Election

#### PowerShell

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/raft/elect" -Method POST
```

#### curl / Git Bash / Linux / macOS

```bash
curl -X POST http://localhost:8000/api/raft/elect
```

This makes the first available alive node start a Raft election. If it receives votes from a majority, it becomes the leader.

### Send Raft Client Request

#### PowerShell

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/api/raft/request" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"value":"set x = 100"}'
```

#### curl.exe on PowerShell

```powershell
curl.exe -X POST "http://localhost:8000/api/raft/request" -H "Content-Type: application/json" -d "{\"value\":\"set x = 100\"}"
```

#### Linux / macOS / Git Bash

```bash
curl -X POST http://localhost:8000/api/raft/request \
  -H "Content-Type: application/json" \
  -d '{"value":"set x = 100"}'
```

Expected behavior:

- If there is no leader, the gateway starts an election automatically.
- The leader appends the command to its log.
- The leader sends `AppendEntries` requests to followers.
- Once a majority acknowledges the entry, it is committed.
- The command `set x = 100` is applied to the state machine.

---

## Paxos Examples

### Send Paxos Request

#### PowerShell

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/api/paxos/request" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"value":"set y = 200"}'
```

#### curl.exe on PowerShell

```powershell
curl.exe -X POST "http://localhost:8000/api/paxos/request" -H "Content-Type: application/json" -d "{\"value\":\"set y = 200\"}"
```

#### Linux / macOS / Git Bash

```bash
curl -X POST http://localhost:8000/api/paxos/request \
  -H "Content-Type: application/json" \
  -d '{"value":"set y = 200"}'
```

Expected behavior:

- A proposer chooses a proposal number.
- The proposer sends `Prepare` messages to acceptors.
- If a majority replies with promises, the proposer sends `Accept` messages.
- If a majority accepts the value, the value becomes chosen.
- The proposer sends `Learn` messages so nodes apply the value.

---

## Zab Examples

### Recover / Elect Zab Primary

#### PowerShell

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/zab/recover" -Method POST
```

#### curl / Git Bash / Linux / macOS

```bash
curl -X POST http://localhost:8000/api/zab/recover
```

### Send Zab Request

#### PowerShell

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/api/zab/request" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"value":"set z = 300"}'
```

#### curl.exe on PowerShell

```powershell
curl.exe -X POST "http://localhost:8000/api/zab/request" -H "Content-Type: application/json" -d "{\"value\":\"set z = 300\"}"
```

#### Linux / macOS / Git Bash

```bash
curl -X POST http://localhost:8000/api/zab/request \
  -H "Content-Type: application/json" \
  -d '{"value":"set z = 300"}'
```

Expected behavior:

- If there is no primary, recovery is triggered to elect one.
- The primary assigns a new `zxid`.
- The primary sends `PROPOSE` messages to followers.
- The primary waits for quorum acknowledgements.
- The primary sends `COMMIT`.
- The value is applied in `zxid` order.

---

## Failure and Recovery

You can simulate node failures and recoveries.

### Fail Node

Example: fail `N3`.

#### PowerShell

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/nodes/N3/fail" -Method POST
```

#### curl / Git Bash / Linux / macOS

```bash
curl -X POST http://localhost:8000/api/nodes/N3/fail
```

### Recover Node

#### PowerShell

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/nodes/N3/recover" -Method POST
```

#### curl / Git Bash / Linux / macOS

```bash
curl -X POST http://localhost:8000/api/nodes/N3/recover
```

### Important Quorum Note

The project runs with 5 nodes, so the quorum size is:

```text
floor(5 / 2) + 1 = 3
```

This means the protocols need at least 3 alive nodes to reach a decision.

---

## PowerShell Notes

On Windows PowerShell, `curl` is often an alias for `Invoke-WebRequest`, not the real curl executable. Because of this, you may see an error like:

```text
A parameter cannot be found that matches parameter name 'X'
```

Use one of the following solutions.

### 1. Use Invoke-RestMethod

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/api/raft/request" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"value":"set x = 100"}'
```

### 2. Use curl.exe

```powershell
curl.exe -X POST "http://localhost:8000/api/raft/request" -H "Content-Type: application/json" -d "{\"value\":\"set x = 100\"}"
```

### 3. Do not use `^` in PowerShell

The `^` character is used for line continuation in CMD. In PowerShell, use the backtick character instead:

```powershell
`
```

---

## How the Algorithms Work

## Raft

Raft in this project is based on a single leader that receives client commands and replicates them to followers.

### Implemented Flow

1. A node starts as a follower.
2. When needed, a node starts an election and becomes a candidate.
3. The candidate sends `RequestVote` messages to the other nodes.
4. If it receives votes from a majority, it becomes the leader.
5. The leader receives a client request.
6. The leader appends the command to its log.
7. The leader sends `AppendEntries` messages to followers.
8. If a majority of nodes acknowledge the entry, it is committed.
9. The command is applied to the state machine.
10. A heartbeat is sent to update followers with the latest commit index.

### Raft Node Endpoints

```text
POST /raft/request-vote
POST /raft/append-entries
POST /raft/start-election
POST /raft/client-request
```

---

## Paxos

Paxos in this project demonstrates agreement on a value using two main phases: Prepare and Accept.

### Implemented Flow

1. A proposer chooses a proposal number.
2. The proposer sends `Prepare(n)` to all acceptors.
3. Each acceptor replies with a `Promise` if the proposal number is higher than any previous proposal number it has promised.
4. If the proposer receives quorum promises, it moves to the Accept phase.
5. The proposer sends `Accept(n, value)`.
6. If a majority of acceptors accept the value, the value becomes chosen.
7. The proposer sends `Learn` messages so nodes apply the value.

### Paxos Node Endpoints

```text
POST /paxos/prepare
POST /paxos/accept
POST /paxos/learn
POST /paxos/propose
```

---

## Zab

Zab, or ZooKeeper Atomic Broadcast, is the atomic broadcast protocol used by Apache ZooKeeper. This project implements a simplified version to demonstrate discovery, synchronization, and broadcast.

### Implemented Flow

1. A primary is selected from the alive nodes.
2. The primary collects discovery information from the other nodes.
3. A new epoch is started.
4. The primary synchronizes followers.
5. When a client request arrives, the primary assigns a new `zxid`.
6. The primary sends `PROPOSE` messages to followers.
7. The primary waits for quorum acknowledgements.
8. The primary sends `COMMIT`.
9. Each node applies the value in `zxid` order.

### Zab Node Endpoints

```text
GET  /zab/discovery-info
POST /zab/sync
POST /zab/recover-cluster
POST /zab/propose
POST /zab/commit
POST /zab/client-request
```

---

## State Machine Commands

The project includes a simple replicated key-value state machine.

The clearly supported command format is:

```text
set key = value
```

Examples:

```text
set x = 100
set user = ali
set mode = active
```

When these commands are successfully committed, they appear inside `kv` in the status response.

Example:

```json
{
  "kv": {
    "x": "100"
  }
}
```

Any command that does not start with `set` is only recorded in `applied` and does not update the `kv` state.

---

## Gateway API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Dashboard |
| GET | `/api/status` | Get cluster status |
| POST | `/api/reset` | Reset all nodes |
| POST | `/api/raft/elect` | Start Raft election |
| POST | `/api/raft/request` | Send a command through Raft |
| POST | `/api/paxos/request` | Send a command through Paxos |
| POST | `/api/zab/recover` | Start Zab recovery / primary selection |
| POST | `/api/zab/request` | Send a command through Zab |
| POST | `/api/nodes/{node_id}/fail` | Mark a node as failed |
| POST | `/api/nodes/{node_id}/recover` | Recover a failed node |

---

## Node Admin API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/admin/status` | Get node status |
| POST | `/admin/fail` | Mark node as failed |
| POST | `/admin/recover` | Recover node |
| POST | `/admin/reset` | Reset node state |

Example direct node status request:

```bash
curl http://localhost:8001/admin/status
```

---

## Testing

To run tests inside a container:

```bash
docker compose exec gateway pytest
```

Or locally, if dependencies are installed:

```bash
pytest
```

---

## Troubleshooting

### Port already in use

If a port is already in use, stop old containers first:

```bash
docker compose down
```

Then start the project again:

```bash
docker compose up --build
```

### Docker is not running

Make sure Docker Desktop is open and running before executing `docker compose up`.

### curl does not work in PowerShell

Use `Invoke-RestMethod` or `curl.exe` instead of `curl`.

### Changes are not reflected

The project uses volumes with reload support, but if changes are not reflected, rebuild the containers:

```bash
docker compose up --build
```

### Reset everything

```bash
docker compose down
```

Then:

```bash
docker compose up --build
```

---

## Limitations

This project is educational and not production-ready. Some simplifications include:

- State is stored only in memory and is not persisted to disk.
- Real network partitions are not simulated.
- Timeouts and randomized elections are simplified.
- Dynamic cluster membership is not implemented.
- Security and authentication are not implemented.
- Durable log storage is not implemented.
- The goal is to explain consensus concepts, not to build a production consensus library.

---

## Suggested Report Description

You can use the following description in a report or documentation:

> This project implements an educational distributed consensus lab using Python, FastAPI, and Docker Compose. The system runs five independent node services that communicate using HTTP. It demonstrates three consensus protocols: Raft, Paxos, and Zab. The implementation includes leader election, quorum-based decision making, log replication, atomic broadcast, node failure and recovery, and a simple replicated key-value state machine. A gateway service and dashboard are provided to interact with the cluster and observe protocol traces in real time.

---

## Suggested LinkedIn / GitHub Summary

> I built a distributed consensus algorithms lab using Python, FastAPI, and Docker Compose. The project runs five independent node containers and demonstrates Raft, Paxos, and Zab through real HTTP communication. It includes leader election, quorum voting, log replication, atomic broadcast, node failure/recovery simulation, and a live dashboard for observing protocol traces.

---

