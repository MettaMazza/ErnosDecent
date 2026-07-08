# ErnOS Diagnostic — Split into individual prompts

Paste **one block at a time** to Echo (as owner). Each is self-contained, runs in one turn, and
ends with its own scorecard table. Run them in order (some later blocks are lighter if earlier
ones already created state, but each also works standalone). Each block already contains its own
instruction line + correct arguments.

**Never-run (destructive/outward — don't include these):** `system_recompile`, `money_transfer`,
`dht_store`, `name_register`, `submit_issue`, `delegate_swarm`, `consolidate_tool(["force"])`,
`seed_curriculum`, `request_clarification`, `test_all_systems` (it RUNS this file — recursion),
`persona_set` with a non-active persona (identity swap mid-validation skews every later block).

---

## 1 — Read-only probes
```
Run ALL below in ONE turn, no questions. For each: call it, log ✅/❌ + one-line reason. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
wallet_balance([]) ; workspace_current([]) ; workspace_list([]) ; workspace_list_links([]) ; list_sessions([]) ; list_lessons([]) ; get_lesson([1]) ; autonomy_history([]) ; performance_review([]) ; changelog([5]) ; operate_scheduler(["list"]) ; moderation_tool(["a harmless diagnostic sentence"]) ; name_resolve(["diagnostic.ernos"]) ; dht_get(["network:host_nodes"]) ; git_tool(["status",""]) ; turing_grid_op(["read",""]) ; delegate_list([]) ; file_info(["node.ep"]) ; codebase_read(["config/edition.json"]) ; codebase_read_range(["node.ep",1,10])
```

## 2 — Reference & retrieval
```
Run ALL below in ONE turn, no questions. Log ✅/❌ + reason each. If no sessions exist, mark read_transcripts ⏭️. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
index_ernos_reference([]) ; lookup_ernos(["string builtins"]) ; rag_retrieve(["ErnosDecent architecture"]) ; search_sessions(["Maria"]) ; read_transcripts(["<a session id from list_sessions/search, else SKIP>"])
```

## 3 — Memory & cognition (round-trips)
```
Run ALL below in ONE turn, no questions. Each is setup→use→cleanup; verify the value round-trips. Log ✅/❌ + reason. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
scratchpad_tool(["write","diag_k","diag_v"]) → scratchpad_tool(["read","diag_k",""]) (expect diag_v) → scratchpad_tool(["forget","diag_k",""]) ; memory_tool(["store","diag_m","diag mem"]) → memory_tool(["get","diag_m",""]) → memory_tool(["forget","diag_m",""]) ; reasoning_tool(["note","diag note"]) → reasoning_tool(["read",""]) → reasoning_tool(["clear",""]) ; timeline_tool(["add","diag event"]) → timeline_tool(["recent","5"]) ; lessons_tool(["add","diag_lesson","diag lesson text"]) → lessons_tool(["get","diag_lesson",""]) ; consolidate_tool([""])
```

## 4 — Graphs (synaptic + knowledge + procedures)
```
Run ALL below in ONE turn, no questions. Log ✅/❌ + reason. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
operate_synaptic_graph(["stats","",""]) ; operate_synaptic_graph(["store","DiagConcept","a diagnostic concept"]) → operate_synaptic_graph(["search","DiagConcept",""]) → operate_synaptic_graph(["relate","DiagConcept","DiagTarget"]) ; kg_tool(["add_entity","DiagEntity","",""]) → kg_tool(["add_relation","DiagEntity","relates_to","DiagOther"]) → kg_tool(["query","DiagEntity","",""]) ; procedure_tool(["store","diag_proc","step 1; step 2"]) → procedure_tool(["get","diag_proc",""]) → procedure_tool(["list","",""])
```

## 5 — Reading progress
```
Run ALL below in ONE turn, no questions. Log ✅/❌ + reason; verify the round-trips. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
manage_reading_progress(["bookmark","diag_doc",3]) → manage_reading_progress(["get_bookmark","diag_doc",""]) (expect 3) → manage_reading_progress(["take_note","diag_doc","a diag note"]) → manage_reading_progress(["get_notes","diag_doc",""])
```

## 6 — Self-prompt & session guidance (RESTORE the real value)
```
Run ALL below in ONE turn, no questions. Log ✅/❌ + reason. IMPORTANT: save the real skills value first and restore it exactly at the end. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
self_prompt_get(["behavior"]) ; self_prompt_get(["skills"]) — SAVE this exact text ; self_prompt_set(["skills","DIAG_TEST_MARKER"]) → self_prompt_get(["skills"]) (expect DIAG_TEST_MARKER) → self_prompt_set(["skills","<the saved text>"]) (RESTORE) ; session_prompt_set(["Diagnostic session guidance — remove after test."]) → session_prompt_get([])
```

## 7 — Workspace files & linking
```
Run ALL below in ONE turn, no questions. Log ✅/❌ + reason. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
workspace_write(["diag.txt","line one\nline two\nline three"]) → workspace_read(["diag.txt"]) → workspace_read_range(["diag.txt",1,2]) → attach_file(["config/workspaces/active/diag.txt"]) (should attach to your reply) ; workspace_link(["/tmp","diagtmp"]) → workspace_list_links([]) → workspace_set_active(["diagtmp"]) → workspace_current([]) → workspace_unlink(["diagtmp"])
```

## 8 — Execution & sandbox (approval prompts appear — approve them)
```
Run ALL below in ONE turn, no questions. run_command and codebase_write each ask approval once. Log ✅/❌ + reason. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
run_ep(["display \"diag run_ep ok\""]) (expect diag run_ep ok) ; run_command(["echo diag_command_ok"]) (expect diag_command_ok) ; codebase_write(["config/workspaces/active/diag_cbw.txt","codebase_write ok"]) → codebase_read(["config/workspaces/active/diag_cbw.txt"])
```

## 9 — Network (may FAIL if offline — record the reason)
```
Run ALL below in ONE turn, no questions. download_tool asks approval once. Log ✅/❌ + reason. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
web_search(["ErnosDecent decentralized AI"]) ; web_visit(["https://example.com"]) ; download_tool(["https://raw.githubusercontent.com/github/gitignore/main/CONTRIBUTING.md"])
```

## 10 — Delegation (spawns a real sub-agent)
```
Run ALL below in ONE turn, no questions. Capture the task_id and reuse it. Log ✅/❌ + reason. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
delegate_task(["Reply with only the single word: DONE.","diagnostic-tester"]) — capture task_id → delegate_check(["<task_id>"]) → delegate_wait(["<task_id>"]) (expect DONE)
```

## 11 — Discord surface (run this ON Discord)
```
Run ALL below in ONE turn, no questions. Log ✅/❌ + reason. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
discord_list_channels([]) → discord_read_channel(["<a channel id from the list>"]) ; react(["✅"]) (should react to THIS message)
```

## 12 — Scheduler round-trip (create → run → delete, leave nothing behind)
```
Run ALL below in ONE turn, no questions. Log ✅/❌ + reason. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
operate_scheduler(["create","diag_job","Post the word tick.","interval","3600"]) → operate_scheduler(["list"]) (expect diag_job) → operate_scheduler(["delete","diag_job","","",""])
```

## 13 — Image generation + vision + attach (SLOW, ~1–3 min)
```
In ONE turn, no questions: generate_image(["a single glossy red cube centered on a plain white background, studio product photo"]). It should return a real DESCRIPTION of the image AND attach the image to your reply. End: reply_request with the description, and a table |tool|result|detail| noting generate_image ✅/❌ (generated?), vision-describe ✅/❌ (accurate?), attach ✅/❌ (on the reply?).
```

## 14 — Sessions by name + persona registry (round-trips, safe)
```
Run ALL below in ONE turn, no questions. Log ✅/❌ + reason. End: reply_request a table |tool|result|detail| + PASS/FAIL count.
session_rename(["diagnostic run"]) → list_sessions([]) (expect the ACTIVE session titled "diagnostic run") → read_transcripts(["diagnostic run"]) (name lookup — expect THIS session's transcript) ; persona_set(["list"]) (expect at least persona "echo"; do NOT activate anything)
```
