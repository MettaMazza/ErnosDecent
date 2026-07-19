# Phase 13: Email, Git, and Consensus — Implementation Plan

> **Archived design record.** This document preserves the Phase 13 proposal; its
> future-tense API list is not current operational documentation. Implemented behavior
> and limitations are recorded in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

This plan outlines the design and implementation details for Phase 13 of ErnosDecent. This phase introduces decentralized application layers (SMTP/IMAP email hosting and P2P Git repository hosting) and the core consensus layer (Raft state replication) required to build distributed trust across the symbiotic mesh.

---

## User Review Required

> [!IMPORTANT]
> - **Git over P2P Storage**: Instead of wrapping around the local `git` executable or parsing complex binary packfiles, the P2P Git server will represent git objects (commits, trees, blobs) directly as content-addressed chunks synced over the DHT and stored using `decent_store/content.ep`. Git pushes will require cryptographic signatures mapping the pusher's DID to the repository's authorized contributor list.
> - **SMTP/IMAP Socket Interop**: The SMTP/IMAP servers will bind to native ports (25 and 143) using socket listeners, mapping traditional email identities (e.g. `alice@ernos`) directly to their DIDs.
> - **Consensus Verification Cluster**: Integration testing of Raft requires running a simulated 3-node network cluster in a single binary process using spawned lightweight threads and channel-based RPC simulation.

---

## Proposed Changes

### Naming & Hosting Subsystem (`decent_host/`)

#### [NEW] [email.ep](../decent_host/email.ep)
API and structures for native SMTP and IMAP hosting:
- `define structure EmailAccount`: fields `email_address as Str`, `owner_did as Str`, `inbox_list as List`, `authenticated_session as Int`.
- `define structure SmtpServer`: fields `port as Int`, `accounts as Map`, `is_running as Int`.
- `define smtp_create_server with port as Int returning Map`
- `define smtp_handle_command with server as Map and cmd_str as Str returning Str` (processes `HELO`, `MAIL FROM`, `RCPT TO`, `DATA`, `QUIT`).
- `define smtp_route_inbound with server as Map and raw_msg as Str returning Int` (verifies sender signature, maps sender to DID, and appends to recipient inbox).
- `define imap_create_server with port as Int returning Map`
- `define imap_handle_command with server as Map and account as Map and cmd_str as Str returning Str` (processes `LOGIN`, `SELECT`, `FETCH`, `LOGOUT`).

#### [NEW] [git.ep](../decent_host/git.ep)
API and structures for secure P2P Git hosting:
- `define structure GitRepo`: fields `repo_name as Str`, `authorized_collaborators as Map` (maps DID -> role), `ref_heads as Map` (maps branch name -> commit_hash), `object_store as Map`.
- `define git_create_repo with name as Str and owner_did as Str returning Map`
- `define git_push_commit with repo as Map and pusher_did as Str and commit_hash as Str and payload as Str and signature as Str returning Int` (validates signature, checks permissions, stores commit object).
- `define git_pull_ref with repo as Map and branch as Str returning Str` (returns branch tip commit hash).

---

### Consensus Subsystem (`decent_consensus/`)

#### [PROPOSED] [raft.ep — later consolidated into state.ep](../decent_consensus/state.ep)
Core Raft consensus state machine:
- `define structure RaftNode`: fields `node_id as Str`, `current_term as Int`, `voted_for as Str`, `log as List`, `commit_index as Int`, `last_applied as Int`, `role as Str`, `peers as List`, `match_index as Map`, `next_index as Map`.
- `define raft_create_node with id as Str and peers as List returning Map`
- `define raft_handle_request_vote with node as Map and term as Int and candidate_id as Str and last_log_index as Int and last_log_term as Int returning Map`
- `define raft_handle_append_entries with node as Map and term as Int and leader_id as Str and prev_log_index as Int and prev_log_term as Int and entries as List and leader_commit as Int returning Map`

#### [NEW] [state.ep](../decent_consensus/state.ep)
Raft replicated log state management:
- `define structure LogEntry`: fields `term as Int`, `index as Int`, `command as Str`.
- `define state_apply_log with node as Map and entry as Map returning Int` (applies the consensus log entry command, e.g. updating a replicated key-value state).
- `define state_rollback_log with node as Map and index as Int returning Int` (handles rolling back uncommitted logs on leader replacement).

#### [NEW] [election.ep](../decent_consensus/election.ep)
Leader election loops and RPC timers:
- `define election_tick with node as Map returning Int` (triggers Candidate status and transitions when election timeout expires).
- `define election_start_vote with node as Map returning Int` (broadcasts RequestVote RPCs to peers).
- `define election_send_heartbeat with node as Map returning Int` (sends empty AppendEntries to assert leadership).

#### [NEW] [test_consensus.ep](../decent_consensus/test_consensus.ep)
Integration test suite for Phase 13:
- Sets up a simulated 3-node cluster.
- Test 1: Leader election. Simulates election timeouts, Candidate transitions, and successful Leader election.
- Test 2: Log replication. Submits commands to the leader and verifies state synchronization to followers.
- Test 3: Network partition recovery. Simulates a network partition, shows that the split group cannot commit entries without a majority, and verifies recovery/log reconciliation once the partition heals.
- Test 4: SMTP/IMAP email signature verification and P2P Git commit pushed with DID signature validation.

---

## Verification Plan

### Automated Tests
- Compile and run the consensus integration suite using:
  `"/Users/mettamazza/Desktop/ErnosPlain Programing Language/target/release/ernos" decent_consensus/test_consensus.ep && ./decent_consensus/test_consensus`
- Validate that all assertions pass (including Raft split-brain protection, SMTP routing signature verification, and Git push auth checks).
