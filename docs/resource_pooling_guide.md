# Resource Pooling User Guide

This guide describes the resource-pooling behavior implemented by the current node.

## Bandwidth pooling

The bandwidth pool records bytes relayed for each registered peer. Uploads increase the contribution score; downloads reduce it by half their byte count. A peer is promoted from `free` to `premium` after its contribution score reaches 52,428,800 bytes. The configured tiers are:

| Tier | Limit | Priority |
|---|---:|---:|
| `free` | 100 kbps | 0 |
| `emergency` | 1,000 kbps | 2 |
| `premium` | 10,000 kbps | 1 |

Download limits are enforced over a mutex-protected 60-second accounting window. The allowance is derived directly from the tier's configured decimal kbps value. A caller cannot claim a tier different from the tier assigned to its peer record.

`bandwidth_route_proxy` opens a real TCP connection to the requested destination, forwards one framed request, receives one framed reply, closes the connection, and records the transferred bytes. Connection, send, receive, accounting, rate-limit, and close failures are returned explicitly. It is a TCP application relay, not a VPN, QUIC proxy, or general IP router.

## Compute pooling

The compute manager maintains a mutex-protected job map, pending queue, worker assignments, submissions, and completed-task contribution counts. Each job requires two distinct assigned workers. Matching submissions complete the job; divergent submissions mark it disputed.

Remote workers use the TCP compute protocol:

1. A worker sends `COMPUTE_REQUEST` with its worker ID.
2. The manager replies with `COMPUTE_ASSIGN` and `job_id:input`, or `COMPUTE_NO_JOBS`.
3. The worker sends `COMPUTE_RESULT` on the same connection.
4. The manager validates the job and worker assignment, records the result, and returns `COMPUTE_ACK` with the exact status code.

The server accepts workers continuously and handles their result-bearing connections concurrently. The protocol uses the existing framed TCP transport and its timeouts.

## Exact boundary

`mesh_execute_collaborative_ai` currently performs both redundant inference calls on the coordinator under two assigned worker identities. It verifies their results through the same compute consensus manager, but it does not automatically dispatch those inference calls to remote TCP workers. The remote worker protocol is operational and tested separately. No UI metric should describe coordinator-local inference as remote compute contribution.
