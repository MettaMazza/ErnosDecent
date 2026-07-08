# ErnOS Full-System Diagnostic — Master Prompt

Copy-paste the block below to Echo (as admin/owner) any time to stress-test **every tool and
subsystem in one ReAct turn** and get a pass/fail report card. It exercises tools in dependency
order (reads first, then setup→use→cleanup, then network/heavy), uses correct arguments, and
explicitly skips the destructive ones.

> Note: this is a genuine stress test — it runs 60+ tool calls in a single turn, so it takes a
> while (the image-gen step alone is a minute+). `run_command` and `codebase_write` will each ask
> for approval once (click Approve). The whole thing is designed to be safe: nothing destructive,
> outward-facing, or irreversible is run.

---

SYSTEM DIAGNOSTIC — run everything below in THIS ONE turn. Do not ask me anything; do not stop
early. Chain the tool calls, and use `mid_message` to post progress every ~10 tools so I can watch.
For EACH numbered item: call the tool exactly as written, then record PASS (returned a sensible
result), FAIL (error/exception — include the error), or SKIP (dependency missing). When an item
depends on a previous result (a session id, a channel id, a task id), take that value from the
earlier output. At the very end, `reply_request` with a markdown **Report Card** table:
`| # | Tool | Result | Detail |` — one row per item, Result = ✅ / ❌ / ⏭️, Detail = one-line reason
or a short snippet of what came back. Finish with a count: `PASS x / FAIL y / SKIP z of N`.

### A. Read-only probes (no setup)
1. `wallet_balance([])`
2. `workspace_current([])`
3. `workspace_list([])`
4. `workspace_list_links([])`
5. `list_sessions([])`
6. `list_lessons([])`
7. `get_lesson([1])`
8. `autonomy_history([])`
9. `performance_review([])`
10. `self_prompt_get(["behavior"])`
11. `session_prompt_get([])`
12. `changelog([5])`
13. `operate_scheduler(["list"])`
14. `procedure_tool(["list", "", ""])`
15. `operate_synaptic_graph(["stats", "", ""])`
16. `moderation_tool(["This is a harmless diagnostic sentence."])`
17. `name_resolve(["diagnostic.ernos"])`
18. `dht_get(["network:host_nodes"])`
19. `git_tool(["status", ""])`
20. `turing_grid_op(["read", ""])`
21. `delegate_list([])`
22. `file_info(["node.ep"])`
23. `codebase_read(["config/edition.json"])`
23b. `codebase_read_range(["node.ep", 1, 10])`  → expect lines 1–10
24. `memory_tool(["list", "", ""])`
25. `timeline_tool(["recent", "5"])`
26. `kg_tool(["query", "Maria", "", ""])`

### B. Reference + retrieval (dependency: index before lookup)
27. `index_ernos_reference([])`
28. `lookup_ernos(["string builtins"])`
29. `rag_retrieve(["ErnosDecent architecture"])`

### C. Stateful tools — setup → use → cleanup (verify the round-trip)
30. `scratchpad_tool(["write", "diag_key", "diag_value"])`
31. `scratchpad_tool(["read", "diag_key", ""])`  → expect `diag_value`
32. `scratchpad_tool(["forget", "diag_key", ""])`
33. `memory_tool(["store", "diag_mem", "diagnostic memory value"])`
34. `memory_tool(["get", "diag_mem", ""])`  → expect the value
35. `memory_tool(["forget", "diag_mem", ""])`
36. `workspace_write(["diag.txt", "line one\nline two\nline three"])`
37. `workspace_read(["diag.txt"])`  → expect the 3 lines
38. `workspace_read_range(["diag.txt", 1, 2])`  → expect lines 1–2
38b. `attach_file(["config/workspaces/active/diag.txt"])`  → the diag.txt from #36 should ride WITH your final reply as an attachment
39. `lessons_tool(["add", "diag_lesson", "diagnostic lesson text"])`
40. `lessons_tool(["get", "diag_lesson", ""])`
41. `reasoning_tool(["note", "diagnostic reasoning note"])`
42. `reasoning_tool(["read", ""])`  → expect the note
43. `reasoning_tool(["clear", ""])`
44. `timeline_tool(["add", "diagnostic timeline event"])`
45. `operate_synaptic_graph(["store", "DiagConcept", "a diagnostic concept for testing"])`
46. `operate_synaptic_graph(["search", "DiagConcept", ""])`
47. `operate_synaptic_graph(["relate", "DiagConcept", "DiagTarget"])`
48. `kg_tool(["add_entity", "DiagEntity", "", ""])`
49. `kg_tool(["add_relation", "DiagEntity", "relates_to", "DiagOther"])`
50. `procedure_tool(["store", "diag_proc", "step 1; step 2; step 3"])`
51. `procedure_tool(["get", "diag_proc", ""])`
52. `manage_reading_progress(["bookmark", "diag_doc", 3])`
53. `manage_reading_progress(["get_bookmark", "diag_doc", ""])`  → expect 3
54. `manage_reading_progress(["take_note", "diag_doc", "a diagnostic note"])`
55. `manage_reading_progress(["get_notes", "diag_doc", ""])`
56. `session_prompt_set(["Diagnostic session guidance — remove after test."])`
57. `session_prompt_get([])`  → expect the guidance
58. `consolidate_tool([""])`  (non-force)

### D. Self-prompt (set → verify → RESTORE — do not leave the test value)
59. `self_prompt_get(["skills"])`  — SAVE this exact value.
60. `self_prompt_set(["skills", "DIAG_TEST_MARKER"])`
61. `self_prompt_get(["skills"])`  → expect `DIAG_TEST_MARKER`
62. `self_prompt_set(["skills", "<the value you saved in #59>"])`  — RESTORE it exactly.

### E. Workspace linking — round-trip (link → activate → unlink)
63. `workspace_link(["/tmp", "diagtmp"])`
64. `workspace_list_links([])`  → expect `diagtmp`
65. `workspace_set_active(["diagtmp"])`
66. `workspace_unlink(["diagtmp"])`

### F. Execution + sandbox (run_command asks approval once — approve it)
67. `run_ep(["display \"diag run_ep ok\""])`  → expect `diag run_ep ok`
68. `run_command(["echo diag_command_ok"])`  → expect `diag_command_ok` (approval required)
69. `codebase_write(["config/workspaces/active/diag_cbw.txt", "codebase_write diagnostic ok"])` (approval required)
70. `codebase_read(["config/workspaces/active/diag_cbw.txt"])`  → expect the content

### G. Network (may FAIL if offline — record the reason, don't retry endlessly)
71. `web_search(["ErnosDecent decentralized AI"])`
72. `web_visit(["https://example.com"])`
73. `download_tool(["https://raw.githubusercontent.com/github/gitignore/main/CONTRIBUTING.md"])` (approval; small text file)

### H. Sessions (dependency: pick an id from #5 output)
74. `search_sessions(["Maria"])`
75. `read_transcripts(["<a session id from #5 or #74; if none exist, SKIP>"])`

### I. Delegation (spawns a real sub-agent — dependency: use the returned task_id)
76. `delegate_task(["Reply with only the single word: DONE.", "diagnostic-tester"])`  — capture the task_id.
77. `delegate_check(["<task_id from #76>"])`
78. `delegate_wait(["<task_id from #76>"])`  → expect the sub-agent's DONE

### J. Discord surface (only meaningful on a Discord turn — else SKIP with that reason)
79. `discord_list_channels([])`
80. `discord_read_channel(["<a channel id from #79; else SKIP>"])`
81. `react(["✅"])`  — should react to THIS message.

### K. Scheduler round-trip (create → run → delete; leave nothing behind)
82. `operate_scheduler(["create", "diag_job", "Post the word tick.", "interval", "3600"])`
83. `operate_scheduler(["list"])`  → expect `diag_job`
84. `operate_scheduler(["delete", "diag_job", "", "", ""])`

### L. Image generation + vision loop (SLOW — Flux ~1–3 min; tests gen + describe + attach)
85. `generate_image(["a single glossy red cube centered on a plain white background, studio product photo"])`
    → expect a real description of the image AND the image attached to your final reply.

### DO NOT RUN (destructive / outward-facing / irreversible — list them as ⏭️ SKIPPED with this reason)
- `system_recompile([])` — rebuilds and RESTARTS the node.
- `money_transfer([...])` — real ledger transaction.
- `dht_store([...])` / `name_register([...])` — public network / persistent registration.
- `delegate_swarm([...])` — spawns multiple parallel agents.
- `submit_issue([...])` — creates a persistent outward issue.
- `discord_add_reaction([...])` — superseded by `react([...])` (#81); needs explicit ids.
- `delegate_cancel([...])` / `delegate_swarm` — only relevant to a running/parallel task.
- `consolidate_tool(["force"])` — heavy full re-consolidation (the light `[""]` at #58 covers the path).
- `seed_curriculum([])` — bulk curriculum seeding (not a routine check).
- `request_clarification([...])` — HALTS the turn to ask me a question; it would break this
  single-turn diagnostic. It is exercised implicitly (you followed these instructions without
  needing it); mark it ⏭️ with this reason.
- `mid_message` and `reply_request` are not separate line-items — you exercise them by posting
  progress and delivering this report. Mark both ✅ in the table with that note.

### Report Card
End the turn with `reply_request` containing:
- The `| # | Tool | Result | Detail |` table (every item above — 1–85 plus 23b, 38b, plus
  mid_message/reply_request — and the SKIPPED block).
- A final line: `TOTAL — PASS x / FAIL y / SKIP z`.
- If any FAILED, a short "Top issues" list naming the tool and the exact error.

Clean up anything left over (the diag.txt / diag_cbw.txt workspace files, diag_lesson, diag_proc,
diag_doc notes, DiagConcept/DiagEntity graph nodes) if a `forget`/`delete` action exists for it;
otherwise note it in the report as residual.
