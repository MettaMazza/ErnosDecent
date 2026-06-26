// Auto-generated JavaScript from ErnosPlain

function set_prop(target, key, value) {
    let setFn;
    setFn = Reflect["set"];
    setFn.call(Reflect, target, key, value);
}

function send_msg(ws, payload) {
    let readyState, sendFn;
    if (!ws) {
        return 0;
    }
    readyState = ws["readyState"];
    if ((readyState !== 1)) {
        return 0;
    }
    sendFn = ws["send"];
    sendFn.call(ws, payload);
}

function substring(str, start, len) {
    let subFn;
    if (!str) {
        return "";
    }
    subFn = str["substring"];
    return subFn.call(str, start, (start + len));
}

function string_index_of(str, sub) {
    let idxFn;
    if (!str) {
        return (0 - 1);
    }
    idxFn = str["indexOf"];
    return idxFn.call(str, sub);
}

function string_length(str) {
    if (!str) {
        return 0;
    }
    return str["length"];
}

function escapeHTML(str) {
    let reAmp, reApos, reLt, reQuot, res, reClass, reGt;
    if (!str) {
        return "";
    }
    reClass = window["RegExp"];
    reAmp = Reflect.construct(reClass, ["&", "g"]);
    reLt = Reflect.construct(reClass, ["<", "g"]);
    reGt = Reflect.construct(reClass, [">", "g"]);
    reQuot = Reflect.construct(reClass, ["\"", "g"]);
    reApos = Reflect.construct(reClass, ["'", "g"]);
    res = str.replace(reAmp, "&amp;").replace(reLt, "&lt;").replace(reGt, "&gt;").replace(reQuot, "&quot;").replace(reApos, "&#039;");
    return res;
}

function decodeHTMLEntities(str) {
    let temp;
    if (!str) {
        return "";
    }
    temp = document.createElement("textarea");
    temp.innerHTML = str;
    return temp.value;
}

function setControlsEnabled(enabled) {
    let inputs;
    inputs = document.querySelectorAll("input, button[type='submit'], .btn-primary, .btn-secondary");
    inputs.forEach((el) => {
    isNav = el.closest(".nav-menu");
    if (!isNav) {
        if (!enabled) {
            el.disabled = true;
            el.title = "Connect to daemon to use this feature";
        } else {
            el.disabled = false;
            el.title = "";
        }
    }
});
}

function handleDisconnect() {
    let nodePeers, dhtSize, headerDid, nodeTerm, didFull, chunkCount, indicator, statusText, nodeRole, walletVal;
    window.isConnected = false;
    indicator = document.getElementById("connection-indicator");
    indicator.classList.remove("online");
    indicator.classList.add("offline");
    statusText = indicator.querySelector(".status-text");
    statusText.textContent = "Daemon Offline";
    headerDid = document.getElementById("header-did");
    headerDid.textContent = "—";
    nodeRole = document.getElementById("node-role");
    nodeRole.textContent = "—";
    nodeTerm = document.getElementById("node-term");
    nodeTerm.textContent = "—";
    nodePeers = document.getElementById("node-peers");
    nodePeers.textContent = "—";
    dhtSize = document.getElementById("dht-size");
    dhtSize.textContent = "—";
    didFull = document.getElementById("did-full-string");
    didFull.textContent = "Connect to daemon to view identity";
    walletVal = document.getElementById("wallet-val");
    walletVal.textContent = "—";
    chunkCount = document.getElementById("chunk-count");
    chunkCount.textContent = "—";
    setControlsEnabled(false);
}

function connectDaemon() {
    let ws, wsUrl, hostname, wsClass, port;
    port = (window.location.port || "8080");
    hostname = (window.location.hostname || "127.0.0.1");
    if ((hostname === "localhost")) {
        hostname = "127.0.0.1";
    }
    wsUrl = (((("ws://" + String(hostname)) + ":") + String(port)) + "/ws");
    console.log(("Connecting to Daemon: " + String(wsUrl)));
    wsClass = window["WebSocket"];
    ws = Reflect.construct(wsClass, [wsUrl]);
    window.ws = ws;
    ws.onopen = (event) => {
    console.log("Connected to ErnosDecent Daemon.");
    window.isConnected = true;
    indicator = document.getElementById("connection-indicator");
    indicator.classList.remove("offline");
    indicator.classList.add("online");
    statusText = indicator.querySelector(".status-text");
    statusText.textContent = "Daemon Connected";
    setControlsEnabled(true);
    msgStatus = Object();
    msgStatus.type = "get_status";
    send_msg(ws, JSON.stringify(msgStatus));
    msgIdentity = Object();
    msgIdentity.type = "get_identity";
    send_msg(ws, JSON.stringify(msgIdentity));
    msgWallet = Object();
    msgWallet.type = "get_wallet";
    send_msg(ws, JSON.stringify(msgWallet));
    msgStorage = Object();
    msgStorage.type = "get_storage";
    send_msg(ws, JSON.stringify(msgStorage));
    msgPool = Object();
    msgPool.type = "get_pool";
    send_msg(ws, JSON.stringify(msgPool));
    msgNetwork = Object();
    msgNetwork.type = "get_network";
    send_msg(ws, JSON.stringify(msgNetwork));
    msgHosts = Object();
    msgHosts.type = "dht_get";
    msgHosts.key = "network:host_nodes";
    send_msg(ws, JSON.stringify(msgHosts));
    msgMemory = Object();
    msgMemory.type = "get_agent_memory";
    send_msg(ws, JSON.stringify(msgMemory));
    msgTuring = Object();
    msgTuring.type = "get_turing_grid";
    send_msg(ws, JSON.stringify(msgTuring));
    msgModels = Object();
    msgModels.type = "get_ai_models";
    send_msg(ws, JSON.stringify(msgModels));
    msgPlatforms = Object();
    msgPlatforms.type = "get_platforms";
    send_msg(ws, JSON.stringify(msgPlatforms));
    msgPlugins = Object();
    msgPlugins.type = "get_plugins";
    send_msg(ws, JSON.stringify(msgPlugins));
    msgPrompts = Object();
    msgPrompts.type = "get_prompts";
    send_msg(ws, JSON.stringify(msgPrompts));
    msgSys = Object();
    msgSys.type = "get_system_config";
    send_msg(ws, JSON.stringify(msgSys));
    msgSessActive = Object();
    msgSessActive.type = "session_get_active";
    send_msg(ws, JSON.stringify(msgSessActive));
    activeTab = (window.localStorage.getItem("ernode_active_tab") || "overview");
    if ((activeTab === "guide")) {
        navList = document.getElementById("guide-nav-list");
        if (navList) {
            activeBtn = navList.querySelector("button.active");
            if (activeBtn) {
                file = activeBtn.getAttribute("data-guide-file");
                msg = Object();
                msg.type = "gitdec_get_repo_file";
                msg.repo_id = "ErnosDecent";
                msg.filename = file;
                send_msg(ws, JSON.stringify(msg));
            }
        }
    }
};
    ws.onmessage = (event) => {
    dataStr = event.data;
    msg = JSON.parse(dataStr);
    handleDaemonMessage(msg);
};
    ws.onclose = (event) => {
    console.log("Daemon disconnected.");
    handleDisconnect();
    setTimeout((dummy) => {
    connectDaemon();
}, 5000);
};
    ws.onerror = (event) => {
    console.log("Daemon connection error.");
};
}

function saveChatMessage(chanName, sender, text, type, timeStr) {
    let historyStr, channelList, historyObj, msg, hasChannel;
    historyStr = window.localStorage.getItem("ernode_chat_history");
    historyObj = Object();
    if (historyStr) {
        historyObj = JSON.parse(historyStr);
    }
    hasChannel = Reflect.has(historyObj, chanName);
    if (!hasChannel) {
        set_prop(historyObj, chanName, []);
    }
    channelList = historyObj[chanName];
    msg = Object();
    msg.sender = sender;
    msg.text = text;
    msg.type = type;
    msg.time = timeStr;
    channelList.push(msg);
    window.localStorage.setItem("ernode_chat_history", JSON.stringify(historyObj));
}

function saveAiMessage(sender, text, type, timeStr) {
    let historyStr, historyList, msg;
    historyStr = window.localStorage.getItem("ernode_ai_history");
    historyList = [];
    if (historyStr) {
        historyList = JSON.parse(historyStr);
    }
    msg = Object();
    msg.sender = sender;
    msg.text = text;
    msg.type = type;
    msg.time = timeStr;
    historyList.push(msg);
    window.localStorage.setItem("ernode_ai_history", JSON.stringify(historyList));
}

function renderChatHistory(chanName) {
    let historyStr, channelList, hasChannel, historyObj;
    window.chatContainer.innerHTML = "";
    historyStr = window.localStorage.getItem("ernode_chat_history");
    if (!historyStr) {
        appendMessage(window.chatContainer, "system", ("Welcome to #" + String(chanName)), "received");
        return 0;
    }
    historyObj = JSON.parse(historyStr);
    hasChannel = Reflect.has(historyObj, chanName);
    if (!hasChannel) {
        appendMessage(window.chatContainer, "system", ("Welcome to #" + String(chanName)), "received");
        return 0;
    }
    channelList = historyObj[chanName];
    channelList.forEach((msg) => {
    appendMessageRaw(window.chatContainer, msg.sender, msg.text, msg.type, msg.time);
});
    return 0;
}

function renderAiHistory() {
    let historyStr, historyList;
    window.aiContainer.innerHTML = "";
    historyStr = window.localStorage.getItem("ernode_ai_history");
    if (!historyStr) {
        appendMessageRaw(window.aiContainer, "AI (Local Model)", "Greetings! I am loaded inside the decent_ai subsystem. My weights are decoded using Float32 fixed-point attention queries. Ask me anything.", "received", "00:00");
        return 0;
    }
    historyList = JSON.parse(historyStr);
    historyList.forEach((msg) => {
    appendMessageRaw(window.aiContainer, msg.sender, msg.text, msg.type, msg.time);
});
    return 0;
}

function appendMessageRaw(container, sender, text, type, timeStr) {
    let escapedText, bubble;
    bubble = document.createElement("div");
    bubble.className = ("chat-bubble " + String(type));
    escapedText = escapeHTML(text).replace("\n", "<br>");
    bubble.innerHTML = (((((("<span class=\"sender\">" + String(escapeHTML(sender))) + "</span><p>") + String(escapedText)) + "</p><span class=\"timestamp\">") + String(escapeHTML(timeStr))) + "</span>");
    container.appendChild(bubble);
    if (((container === window.aiContainer) && (type === "received"))) {
        attachTtsButton(bubble, text);
    }
    container.scrollTop = container.scrollHeight;
}

function requestTts(text, btn) {
    let ttsMsg;
    if (!text) {
        return 0;
    }
    if ((text.length === 0)) {
        return 0;
    }
    if (!window.ws) {
        return 0;
    }
    if (!window.isConnected) {
        return 0;
    }
    set_prop(btn, "disabled", true);
    btn.textContent = "⏳";
    window.pendingTtsBtn = btn;
    ttsMsg = Object();
    ttsMsg.type = "tts_request";
    ttsMsg.text = text;
    send_msg(window.ws, JSON.stringify(ttsMsg));
    return 0;
}

function attachTtsButton(bubble, text) {
    let btn;
    btn = document.createElement("button");
    btn.className = "btn-tts";
    btn.title = "Play audio (Fable voice)";
    btn.textContent = "🔊";
    btn.onclick = (e) => {
    requestTts(text, btn);
};
    bubble.appendChild(btn);
    return 0;
}

function appendMessage(container, sender, text, type) {
    let timeStrSec, secParts, timeStr, dateStr, timeParts;
    dateStr = Date();
    timeParts = dateStr.split(" ");
    timeStrSec = timeParts[4];
    secParts = timeStrSec.split(":");
    timeStr = (secParts[0] + (":" + secParts[1]));
    appendMessageRaw(container, sender, text, type, timeStr);
    if ((container === window.chatContainer)) {
        saveChatMessage(window.activeChannel, sender, text, type, timeStr);
    } else if ((container === window.aiContainer)) {
        saveAiMessage(sender, text, type, timeStr);
    }
}

function appendAiToken(token) {
    let bubble, textNode;
    if (!window.currentAiResponseBubble) {
        bubble = document.createElement("div");
        bubble.className = "chat-bubble received ai-bot";
        bubble.innerHTML = "<span class=\"sender\">AI (Local Model)</span><p class=\"ai-text\"></p>";
        window.aiContainer.appendChild(bubble);
        window.currentAiResponseBubble = bubble;
    }
    textNode = window.currentAiResponseBubble.querySelector(".ai-text");
    textNode.textContent = (textNode.textContent + token);
    window.aiContainer.scrollTop = window.aiContainer.scrollHeight;
}

function appendApprovalCard(toolName, summary) {
    let bubble, contentHtml, escapedSummary, actionsHtml, denyBtn, btnSubmit, approveBtn, escapedTool, approveAllBtn;
    bubble = document.createElement("div");
    bubble.className = "chat-bubble received";
    set_prop(bubble.style, "border", "1px solid rgba(245, 158, 11, 0.3)");
    set_prop(bubble.style, "background", "rgba(245, 158, 11, 0.05)");
    set_prop(bubble.style, "animation", "approvalPulse 2s infinite");
    escapedTool = escapeHTML(toolName);
    escapedSummary = escapeHTML(summary);
    contentHtml = "<span class=\"sender\">System (Approval Required)</span>";
    contentHtml = (contentHtml + (((("<p>🔒 <strong>Tool Approval Required</strong><br><code class=\"small-code\">Tool: " + String(escapedTool)) + "</code><br><code class=\"small-code\">Args: ") + String(escapedSummary)) + "</code></p>"));
    actionsHtml = "<div class=\"approval-actions\">";
    actionsHtml = (actionsHtml + "<button class=\"btn-approve\" id=\"btn-approve-action\">Approve ✅</button>");
    actionsHtml = (actionsHtml + "<button class=\"btn-approve-all\" id=\"btn-approve-all-action\">Approve All ⚡</button>");
    actionsHtml = (actionsHtml + "<button class=\"btn-deny\" id=\"btn-deny-action\">Deny ❌</button>");
    actionsHtml = (actionsHtml + "</div>");
    set_prop(bubble, "innerHTML", (contentHtml + actionsHtml));
    window.aiContainer.appendChild(bubble);
    set_prop(window.aiContainer, "scrollTop", window.aiContainer.scrollHeight);
    set_prop(window.aiInput, "disabled", true);
    btnSubmit = document.getElementById("btn-submit-ai");
    if ((btnSubmit !== 0)) {
        set_prop(btnSubmit, "disabled", true);
    }
    approveBtn = bubble.querySelector("#btn-approve-action");
    approveAllBtn = bubble.querySelector("#btn-approve-all-action");
    denyBtn = bubble.querySelector("#btn-deny-action");
    approveBtn.onclick = (f) => {
    set_prop(approveBtn, "disabled", true);
    set_prop(approveAllBtn, "disabled", true);
    set_prop(denyBtn, "disabled", true);
    set_prop(bubble.style, "animation", "none");
    set_prop(bubble.style, "border", "1px solid rgba(16, 185, 129, 0.3)");
    set_prop(bubble.style, "background", "rgba(16, 185, 129, 0.03)");
    actionsDiv = bubble.querySelector(".approval-actions");
    set_prop(actionsDiv.style, "display", "none");
    statusText = document.createElement("div");
    statusText.className = "status-label";
    set_prop(statusText.style, "color", "var(--neon-green)");
    set_prop(statusText.style, "padding", "10px 18px");
    set_prop(statusText, "innerHTML", (("✅ Approved `" + String(escapedTool)) + "` — executing..."));
    bubble.appendChild(statusText);
    approveMsg = "{\"type\":\"tool_approve\"}";
    set_prop(window.ws, "send", approveMsg);
};
    approveAllBtn.onclick = (f) => {
    set_prop(approveBtn, "disabled", true);
    set_prop(approveAllBtn, "disabled", true);
    set_prop(denyBtn, "disabled", true);
    set_prop(bubble.style, "animation", "none");
    set_prop(bubble.style, "border", "1px solid rgba(168, 85, 247, 0.3)");
    set_prop(bubble.style, "background", "rgba(168, 85, 247, 0.03)");
    actionsDiv = bubble.querySelector(".approval-actions");
    set_prop(actionsDiv.style, "display", "none");
    statusText = document.createElement("div");
    statusText.className = "status-label";
    set_prop(statusText.style, "color", "var(--neon-purple)");
    set_prop(statusText.style, "padding", "10px 18px");
    set_prop(statusText, "innerHTML", (("⚡ Approved `" + String(escapedTool)) + "` and all subsequent actions — executing..."));
    bubble.appendChild(statusText);
    approveAllMsg = "{\"type\":\"tool_approve_all\"}";
    set_prop(window.ws, "send", approveAllMsg);
};
    denyBtn.onclick = (f) => {
    set_prop(approveBtn, "disabled", true);
    set_prop(approveAllBtn, "disabled", true);
    set_prop(denyBtn, "disabled", true);
    set_prop(bubble.style, "animation", "none");
    set_prop(bubble.style, "border", "1px solid rgba(239, 68, 68, 0.3)");
    set_prop(bubble.style, "background", "rgba(239, 68, 68, 0.03)");
    actionsDiv = bubble.querySelector(".approval-actions");
    set_prop(actionsDiv.style, "display", "none");
    statusText = document.createElement("div");
    statusText.className = "status-label";
    set_prop(statusText.style, "color", "var(--neon-red)");
    set_prop(statusText.style, "padding", "10px 18px");
    set_prop(statusText, "innerHTML", (("❌ Denied `" + String(escapedTool)) + "` — cancelled."));
    bubble.appendChild(statusText);
    set_prop(window.aiInput, "disabled", false);
    if ((btnSubmit !== 0)) {
        set_prop(btnSubmit, "disabled", false);
    }
    denyMsg = "{\"type\":\"tool_deny\"}";
    set_prop(window.ws, "send", denyMsg);
};
}

function appendClarifyCard(questionsJson) {
    let nq, stopB, bubble, questions;
    questions = JSON.parse(questionsJson);
    bubble = document.createElement("div");
    bubble.className = "chat-bubble received";
    set_prop(bubble.style, "border", "1px solid rgba(59, 130, 246, 0.35)");
    set_prop(bubble.style, "background", "rgba(59, 130, 246, 0.06)");
    window.clarifyHtml = "<span class=\"sender\">ErnOS needs a little more to get this right</span>";
    window.clarifyCount = 0;
    questions.forEach((q, idx) => {
    parts = q.split("||");
    qtext = parts[0];
    block = ("<div class=\"clarify-q\" style=\"margin:10px 0;\"><p style=\"margin:0 0 6px;\"><strong>" + (escapeHTML(qtext) + "</strong></p><div>"));
    nparts = parts["length"];
    oi = 1;
    while ((oi < nparts)) {
        opt = parts[oi];
        block = (block + ("<button type=\"button\" class=\"clarify-opt btn-secondary\" data-qi=\"" + (String(idx) + ("\" data-val=\"" + (escapeHTML(opt) + ("\">" + (escapeHTML(opt) + "</button> ")))))));
        oi = (oi + 1);
    }
    block = (block + ("<input type=\"text\" class=\"clarify-text\" data-qi=\"" + (String(idx) + "\" placeholder=\"or type your own\" style=\"margin-top:6px;width:90%;\">")));
    block = (block + "</div></div>");
    window.clarifyHtml = (window.clarifyHtml + block);
    window.clarifyCount = (window.clarifyCount + 1);
});
    window.clarifyHtml = (window.clarifyHtml + "<div class=\"clarify-actions\" style=\"margin-top:8px;\"><button type=\"button\" class=\"clarify-send btn-primary\">Send answers</button> <button type=\"button\" class=\"clarify-current btn-secondary\">Work with what we have</button></div>");
    set_prop(bubble, "innerHTML", window.clarifyHtml);
    window.aiContainer.appendChild(bubble);
    set_prop(window.aiContainer, "scrollTop", window.aiContainer.scrollHeight);
    set_prop(window.aiLoader.style, "display", "none");
    set_prop(window.aiInput, "disabled", true);
    stopB = document.getElementById("btn-stop-ai");
    if ((stopB !== 0)) {
        set_prop(stopB.style, "display", "none");
    }
    nq = window.clarifyCount;
    bubble.addEventListener("click", (e) => {
    tgt = e["target"];
    cls = tgt["className"];
    if (!cls) {
        return 0;
    }
    finder = cls["indexOf"];
    if ((finder.call(cls, "clarify-opt") >= 0)) {
        qa = tgt.getAttribute("data-qi");
        va = tgt.getAttribute("data-val");
        set_prop(bubble, ("data-ans-" + qa), va);
        set_prop(tgt.style, "background", "var(--neon-green, #10b981)");
        set_prop(tgt.style, "color", "#0b1220");
        return 0;
    }
    if ((finder.call(cls, "clarify-current") >= 0)) {
        acts = bubble.querySelector(".clarify-actions");
        if (acts) {
            set_prop(acts.style, "display", "none");
        }
        mc = Object();
        mc.type = "clarify_answer";
        mc.answers = "__USE_CURRENT__";
        send_msg(window.ws, JSON.stringify(mc));
        set_prop(window.aiLoader.style, "display", "flex");
        return 0;
    }
    if ((finder.call(cls, "clarify-send") >= 0)) {
        ans = "";
        k = 0;
        while ((k < nq)) {
            picked = bubble.getAttribute(("data-ans-" + String(k)));
            if (!picked) {
                ti = bubble.querySelector(("input.clarify-text[data-qi=\"" + (String(k) + "\"]")));
                if (ti) {
                    picked = ti["value"];
                }
            }
            if (picked) {
                if ((ans.length > 0)) {
                    ans = (ans + " | ");
                }
                ans = (ans + ("Q" + (String((k + 1)) + (": " + picked))));
            }
            k = (k + 1);
        }
        acts = bubble.querySelector(".clarify-actions");
        if (acts) {
            set_prop(acts.style, "display", "none");
        }
        ms = Object();
        ms.type = "clarify_answer";
        ms.answers = ans;
        send_msg(window.ws, JSON.stringify(ms));
        set_prop(window.aiLoader.style, "display", "flex");
        return 0;
    }
});
}

function appendReasoningBubble(b64) {
    let html, decoded, bubble;
    decoded = decodeURIComponent(escape(atob(b64)));
    bubble = document.createElement("div");
    bubble.className = "chat-bubble received";
    set_prop(bubble.style, "opacity", "0.78");
    set_prop(bubble.style, "fontSize", "0.85em");
    html = ("<details><summary style=\"cursor:pointer;\">💭 Reasoning</summary><pre style=\"white-space:pre-wrap;margin:6px 0 0;\">" + (escapeHTML(decoded) + "</pre></details>"));
    set_prop(bubble, "innerHTML", html);
    window.aiContainer.appendChild(bubble);
    set_prop(window.aiContainer, "scrollTop", window.aiContainer.scrollHeight);
}

function updateHostsTableUI(jsonStr) {
    let tbody, primary, electedHostEl, i, list;
    tbody = document.getElementById("hosts-table-body");
    if (!tbody) {
        return 0;
    }
    tbody.innerHTML = "";
    list = JSON.parse(jsonStr);
    if ((!list || (list.length === 0))) {
        tbody.innerHTML = "<tr><td colspan=\"5\" style=\"text-align: center; color: var(--text-muted); padding: 20px;\">No active host nodes registered in the DHT network tree.</td></tr>";
        return 0;
    }
    electedHostEl = document.getElementById("ui-current-elected-host");
    if (electedHostEl) {
        if ((list.length > 0)) {
            primary = list[0];
            electedHostEl.textContent = (((((String(primary.node_id) + " (") + String(primary.address)) + ":") + String(primary.port)) + ")");
        } else {
            electedHostEl.textContent = "—";
        }
    }
    i = 0;
    list.forEach((host) => {
    i = (i + 1);
    row = document.createElement("tr");
    rankText = i.toString();
    if ((i === 1)) {
        rankText = "🏆 1 (Primary Host)";
    }
    priorityText = "Standard";
    if ((host.is_static === 1)) {
        priorityText = "⭐ Static Preferred";
    }
    lastSeenDiff = Math.max(0, (Math.floor((Date.now() / 1000)) - host.last_seen));
    lastSeenText = (String(lastSeenDiff) + "s ago");
    if ((lastSeenDiff > 120)) {
        lastSeenText = "Stale";
    }
    row.innerHTML = (((((((((((((("<td>" + String(rankText)) + "</td><td><code>") + String(escapeHTML(host.node_id))) + "</code><br><span style=\"font-size:0.8rem;color:var(--text-muted);\">") + String(escapeHTML(host.address))) + ":") + String(host.port)) + "</span></td><td>") + String(host.connections)) + " connection(s)</td><td>") + String(priorityText)) + "</td><td>") + String(lastSeenText)) + "</td>");
    tbody.appendChild(row);
});
    return 0;
}

function handleDhtResult(msg) {
    let dhtLog, entry;
    if ((msg.key === "network:host_nodes")) {
        if (msg.found) {
            updateHostsTableUI(msg.value);
        }
        return 0;
    }
    dhtLog = document.getElementById("dht-log");
    if (!dhtLog) {
        return 0;
    }
    entry = document.createElement("div");
    entry.className = "dht-log-entry";
    if ((msg.action === "store")) {
        entry.textContent = ("✓ Stored key: " + String(msg.key));
        entry.style.color = "var(--color-success)";
    } else if ((msg.action === "get")) {
        if (msg.found) {
            entry.textContent = ((("↓ " + String(msg.key)) + " = ") + String(msg.value));
            entry.style.color = "var(--color-accent)";
        } else {
            entry.textContent = ("✗ Key not found: " + String(msg.key));
            entry.style.color = "var(--color-error)";
        }
    }
    dhtLog.appendChild(entry);
    dhtLog.scrollTop = dhtLog.scrollHeight;
}

function handleNameResult(msg) {
    let entry, headerDid, nameLog;
    nameLog = document.getElementById("name-log");
    if (!nameLog) {
        return 0;
    }
    entry = document.createElement("div");
    entry.className = "name-log-entry";
    if ((msg.action === "register")) {
        if (msg.success) {
            entry.textContent = (((("✓ Registered: " + String(msg.name)) + " → ") + String(substring(msg.did, 0, 25))) + "...");
            entry.style.color = "var(--color-success)";
            headerDid = document.getElementById("header-did");
            if (headerDid) {
                headerDid.textContent = msg.name;
            }
        } else {
            entry.textContent = ("✗ Registration failed: " + String(msg.name));
            entry.style.color = "var(--color-error)";
        }
    } else if ((msg.action === "resolve")) {
        if (msg.found) {
            entry.textContent = ((("↓ " + String(msg.name)) + " → ") + String(msg.did));
            entry.style.color = "var(--color-accent)";
        } else {
            entry.textContent = ("✗ Name not found: " + String(msg.name));
            entry.style.color = "var(--color-error)";
        }
    }
    nameLog.appendChild(entry);
    nameLog.scrollTop = nameLog.scrollHeight;
}

function selectAiModel(modelName, skipSave) {
    let modelText, btns, aiModelSelect, msg;
    window.selectedAiModel = modelName;
    aiModelSelect = document.getElementById("ai-model-select");
    if (aiModelSelect) {
        aiModelSelect.value = modelName;
    }
    if (window.aiModelsListContainer) {
        btns = window.aiModelsListContainer.querySelectorAll("[data-model]");
        btns.forEach((btn) => {
    if ((btn.getAttribute("data-model") === modelName)) {
        btn.classList.add("active");
    } else {
        btn.classList.remove("active");
    }
});
    }
    modelText = (modelName || "Auto (Cascade)");
    appendMessage(window.aiContainer, "system", ("Model set to: " + String(modelText)), "received");
    if (((!skipSave && window.ws) && (window.ws.readyState === 1))) {
        msg = Object();
        msg.type = "session_update_model";
        msg.id = window.activeSessionId;
        msg.model = modelName;
        send_msg(window.ws, JSON.stringify(msg));
    }
}

function updateAiModelsUI(models) {
    let aiModelSelect, currentSelected, activeClass, isIncluded;
    aiModelSelect = document.getElementById("ai-model-select");
    if (aiModelSelect) {
        currentSelected = window.selectedAiModel;
        aiModelSelect.innerHTML = "<option value=\"\">Auto (Cascade)</option>";
        models.forEach((m) => {
    opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    aiModelSelect.appendChild(opt);
});
        aiModelSelect.value = currentSelected;
        if (currentSelected) {
            isIncluded = models.includes(currentSelected);
            if (!isIncluded) {
                window.selectedAiModel = "";
                aiModelSelect.value = "";
            }
        }
    }
    if (window.aiModelsListContainer) {
        activeClass = "";
        if ((window.selectedAiModel === "")) {
            activeClass = "active";
        }
        window.aiModelsListContainer.innerHTML = (("<button class=\"room-item " + String(activeClass)) + "\" data-model=\"\"><span class=\"model-name\">Auto (Cascade)</span><span class=\"model-meta\">GGUF • Active</span></button>");
        models.forEach((m) => {
    itemClass = "";
    if ((window.selectedAiModel === m)) {
        itemClass = "active";
    }
    btn = document.createElement("button");
    btn.className = ("room-item " + String(itemClass));
    btn.setAttribute("data-model", m);
    btn.innerHTML = (("<span class=\"model-name\">" + String(escapeHTML(m))) + "</span><span class=\"model-meta\">Detected • Local</span>");
    window.aiModelsListContainer.appendChild(btn);
});
    }
}

function selectSession(id) {
    let msg;
    window.activeSessionId = id;
    if ((window.isConnected && window.ws)) {
        msg = Object();
        msg.type = "session_switch";
        msg.id = id;
        send_msg(window.ws, JSON.stringify(msg));
    }
    return 0;
}

function renameSession(id, title) {
    let msg;
    msg = Object();
    msg.type = "session_rename";
    msg.id = id;
    msg.title = title;
    send_msg(window.ws, JSON.stringify(msg));
    return 0;
}

function deleteSession(id) {
    let msg;
    msg = Object();
    msg.type = "session_delete";
    msg.id = id;
    send_msg(window.ws, JSON.stringify(msg));
    return 0;
}

function updatePlatformsUI() {
    let telegramConfig, waToggle, waPhoneId, tgStatus, discChannel, waStatus, waToken, statusText, tgToken, discToken, discordConfig, tgToggle, whatsappConfig, discStatus, discToggle;
    if (!window.platforms) {
        return 0;
    }
    discordConfig = window.platforms.discord;
    if (discordConfig) {
        discStatus = document.getElementById("overview-discord-status");
        if (discStatus) {
            statusText = (discordConfig.status || "OFFLINE");
            if (((discordConfig.enabled === false) || (discordConfig.enabled === 0))) {
                statusText = "DISABLED";
            }
            discStatus.textContent = statusText.toUpperCase();
            if ((statusText === "ONLINE")) {
                set_prop(discStatus.style, "background", "rgba(16, 185, 129, 0.15)");
                set_prop(discStatus.style, "color", "var(--neon-green)");
                set_prop(discStatus.style, "border", "1px solid rgba(16, 185, 129, 0.3)");
            } else {
                set_prop(discStatus.style, "background", "rgba(239, 68, 68, 0.15)");
                set_prop(discStatus.style, "color", "var(--neon-red)");
                set_prop(discStatus.style, "border", "1px solid rgba(239, 68, 68, 0.3)");
            }
        }
        discToken = document.getElementById("overview-discord-token");
        if (discToken) {
            discToken.value = (discordConfig.token || "");
        }
        discChannel = document.getElementById("overview-discord-channel");
        if (discChannel) {
            discChannel.value = (discordConfig["channel"] || "");
        }
        discToggle = document.getElementById("toggle-discord");
        if (discToggle) {
            discToggle.checked = (discordConfig.enabled || false);
        }
    }
    whatsappConfig = window.platforms.whatsapp;
    if (whatsappConfig) {
        waStatus = document.getElementById("overview-whatsapp-status");
        if (waStatus) {
            statusText = (whatsappConfig.status || "OFFLINE");
            if (((whatsappConfig.enabled === false) || (whatsappConfig.enabled === 0))) {
                statusText = "DISABLED";
            }
            waStatus.textContent = statusText.toUpperCase();
            if ((statusText === "ONLINE")) {
                set_prop(waStatus.style, "background", "rgba(16, 185, 129, 0.15)");
                set_prop(waStatus.style, "color", "var(--neon-green)");
                set_prop(waStatus.style, "border", "1px solid rgba(16, 185, 129, 0.3)");
            } else {
                set_prop(waStatus.style, "background", "rgba(239, 68, 68, 0.15)");
                set_prop(waStatus.style, "color", "var(--neon-red)");
                set_prop(waStatus.style, "border", "1px solid rgba(239, 68, 68, 0.3)");
            }
        }
        waToken = document.getElementById("overview-whatsapp-token");
        if (waToken) {
            waToken.value = (whatsappConfig.token || "");
        }
        waPhoneId = document.getElementById("overview-whatsapp-phone-id");
        if (waPhoneId) {
            waPhoneId.value = (whatsappConfig.phone_id || "");
        }
        waToggle = document.getElementById("toggle-whatsapp");
        if (waToggle) {
            waToggle.checked = (whatsappConfig.enabled || false);
        }
    }
    telegramConfig = window.platforms.telegram;
    if (telegramConfig) {
        tgStatus = document.getElementById("overview-telegram-status");
        if (tgStatus) {
            statusText = (telegramConfig.status || "OFFLINE");
            if (((telegramConfig.enabled === false) || (telegramConfig.enabled === 0))) {
                statusText = "DISABLED";
            }
            tgStatus.textContent = statusText.toUpperCase();
            if ((statusText === "ONLINE")) {
                set_prop(tgStatus.style, "background", "rgba(16, 185, 129, 0.15)");
                set_prop(tgStatus.style, "color", "var(--neon-green)");
                set_prop(tgStatus.style, "border", "1px solid rgba(16, 185, 129, 0.3)");
            } else {
                set_prop(tgStatus.style, "background", "rgba(239, 68, 68, 0.15)");
                set_prop(tgStatus.style, "color", "var(--neon-red)");
                set_prop(tgStatus.style, "border", "1px solid rgba(239, 68, 68, 0.3)");
            }
        }
        tgToken = document.getElementById("overview-telegram-token");
        if (tgToken) {
            tgToken.value = (telegramConfig.token || "");
        }
        tgToggle = document.getElementById("toggle-telegram");
        if (tgToggle) {
            tgToggle.checked = (telegramConfig.enabled || false);
        }
    }
    return 0;
}

function updatePromptsUI() {
    let personaArea, kernelArea, observerArea;
    if (!window.prompts) {
        return 0;
    }
    kernelArea = document.getElementById("settings-prompt-kernel");
    if (kernelArea) {
        kernelArea.value = (window.prompts.kernel || "");
    }
    personaArea = document.getElementById("settings-prompt-persona");
    if (personaArea) {
        personaArea.value = (window.prompts.persona || "");
    }
    observerArea = document.getElementById("settings-prompt-observer");
    if (observerArea) {
        observerArea.value = (window.prompts.observer || "");
    }
    return 0;
}

function showPromptsStatus(text, isSuccess) {
    let el;
    el = document.getElementById("settings-status-msg");
    if (el) {
        el.textContent = text;
        el.className = "status-msg";
        if ((isSuccess === 1)) {
            el.classList.add("success");
        } else {
            el.classList.add("error");
        }
        setTimeout((dummy) => {
    el.textContent = "";
    el.className = "status-msg";
}, 4000);
    }
    return 0;
}

function renderPluginsUI() {
    let deleteBtns, toggleBtns, body;
    body = document.getElementById("plugins-list-body");
    if (!body) {
        return 0;
    }
    body.innerHTML = "";
    if ((!window.plugins || (window.plugins.length === 0))) {
        body.innerHTML = "<tr><td colspan=\"5\" class=\"empty-state\">No user plugins registered. Click Register Plugin to add custom extensions.</td></tr>";
        return 0;
    }
    window.plugins.forEach((p) => {
    row = document.createElement("tr");
    badgeClass = "badge";
    badgeStyle = "font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600;";
    statusText = "INACTIVE";
    if (p.enabled) {
        statusText = "ACTIVE";
        badgeStyle = (badgeStyle + " background: rgba(16, 185, 129, 0.15); color: var(--neon-green); border: 1px solid rgba(16, 185, 129, 0.3);");
    } else {
        badgeStyle = (badgeStyle + " background: rgba(239, 68, 68, 0.15); color: var(--neon-red); border: 1px solid rgba(239, 68, 68, 0.3);");
    }
    toggleText = "Enable";
    toggleBtnStyle = "padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid var(--border-color); background: rgba(16, 185, 129, 0.1); color: var(--neon-green); margin-right: 6px;";
    if (p.enabled) {
        toggleText = "Disable";
        toggleBtnStyle = "padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid var(--border-color); background: rgba(239, 68, 68, 0.1); color: var(--neon-red); margin-right: 6px;";
    }
    deleteBtnStyle = "padding: 4px 8px; font-size: 11px; border-radius: 4px; cursor: pointer; border: 1px solid rgba(239, 68, 68, 0.3); background: rgba(239, 68, 68, 0.15); color: var(--neon-red);";
    row.innerHTML = (((((((((((((((((((((("<td><strong>" + String(escapeHTML(p.name))) + "</strong></td><td><code>") + String(escapeHTML(p.endpoint))) + "</code></td><td>") + String(escapeHTML(p.desc))) + "</td><td><span class=\"") + String(badgeClass)) + "\" style=\"") + String(badgeStyle)) + "\">") + String(statusText)) + "</span></td><td><button class=\"toggle-plugin-btn\" data-id=\"") + String(escapeHTML(p.id))) + "\" style=\"") + String(toggleBtnStyle)) + "\">") + String(toggleText)) + "</button><button class=\"delete-plugin-btn\" data-id=\"") + String(escapeHTML(p.id))) + "\" style=\"") + String(deleteBtnStyle)) + "\">Delete</button></td>");
    body.appendChild(row);
});
    toggleBtns = body.querySelectorAll(".toggle-plugin-btn");
    toggleBtns.forEach((btn) => {
    btn.addEventListener("click", (event) => {
    id = btn.getAttribute("data-id");
    togglePlugin(id);
});
});
    deleteBtns = body.querySelectorAll(".delete-plugin-btn");
    deleteBtns.forEach((btn) => {
    btn.addEventListener("click", (event) => {
    id = btn.getAttribute("data-id");
    deletePlugin(id);
});
});
    return 0;
}

function togglePlugin(id) {
    if (!window.plugins) {
        return 0;
    }
    window.plugins.forEach((p) => {
    if ((p.id === id)) {
        p.enabled = !p.enabled;
        if (p.enabled) {
            p.status = "ACTIVE";
        } else {
            p.status = "INACTIVE";
        }
    }
});
    savePluginsSettings();
    renderPluginsUI();
    return 0;
}

function deletePlugin(id) {
    let filtered;
    if (!window.plugins) {
        return 0;
    }
    if (!confirm("Are you sure you want to delete this plugin?")) {
        return 0;
    }
    filtered = [];
    window.plugins.forEach((p) => {
    if ((p.id !== id)) {
        filtered.push(p);
    }
});
    window.plugins = filtered;
    savePluginsSettings();
    renderPluginsUI();
    return 0;
}

function savePluginsSettings() {
    let payload;
    if ((!window.ws || !window.isConnected)) {
        return 0;
    }
    payload = Object();
    payload.type = "save_plugins";
    payload.data = JSON.stringify(window.plugins);
    send_msg(window.ws, JSON.stringify(payload));
    return 0;
}

function savePromptsConfig() {
    let personaArea, observerArea, payload, kernelArea;
    if ((!window.ws || !window.isConnected)) {
        showPromptsStatus("Error: Daemon disconnected.", 0);
        return 0;
    }
    kernelArea = document.getElementById("settings-prompt-kernel");
    personaArea = document.getElementById("settings-prompt-persona");
    observerArea = document.getElementById("settings-prompt-observer");
    if (((!kernelArea || !personaArea) || !observerArea)) {
        return 0;
    }
    window.prompts = Object();
    window.prompts.kernel = kernelArea.value;
    window.prompts.persona = personaArea.value;
    window.prompts.observer = observerArea.value;
    payload = Object();
    payload.type = "save_prompts";
    payload.data = JSON.stringify(window.prompts);
    send_msg(window.ws, JSON.stringify(payload));
    return 0;
}

function updateSystemConfigUI() {
    let maxMsg, banThresh, banDur, isStaticHost, dhtTtl, p2pPort, seedPort, maxConn, enableHostElect, dhtPort, dataDir, webPort, heartbeat, relayPort, ipcPort, seedAddr, raftPort, maxContent, electTimeout, logLevel, listenAddr, rateLimit, nodeName;
    if (!window.systemConfig) {
        return 0;
    }
    nodeName = document.getElementById("cfg-node-name");
    if (nodeName) {
        nodeName.value = (window.systemConfig.node_name || "");
    }
    logLevel = document.getElementById("cfg-node-log-level");
    if (logLevel) {
        logLevel.value = (window.systemConfig.node_log_level || "info");
    }
    dataDir = document.getElementById("cfg-node-data-dir");
    if (dataDir) {
        dataDir.value = (window.systemConfig.node_data_dir || "");
    }
    maxContent = document.getElementById("cfg-storage-max-content-size");
    if (maxContent) {
        maxContent.value = (window.systemConfig.storage_max_content_size || 0);
    }
    dhtTtl = document.getElementById("cfg-storage-dht-ttl-sec");
    if (dhtTtl) {
        dhtTtl.value = (window.systemConfig.storage_dht_ttl_sec || 0);
    }
    listenAddr = document.getElementById("cfg-network-listen-address");
    if (listenAddr) {
        listenAddr.value = (window.systemConfig.network_listen_address || "");
    }
    maxConn = document.getElementById("cfg-network-max-connections");
    if (maxConn) {
        maxConn.value = (window.systemConfig.network_max_connections || 0);
    }
    p2pPort = document.getElementById("cfg-network-p2p-port");
    if (p2pPort) {
        p2pPort.value = (window.systemConfig.network_p2p_port || 0);
    }
    dhtPort = document.getElementById("cfg-network-dht-port");
    if (dhtPort) {
        dhtPort.value = (window.systemConfig.network_dht_port || 0);
    }
    relayPort = document.getElementById("cfg-network-relay-port");
    if (relayPort) {
        relayPort.value = (window.systemConfig.network_relay_port || 0);
    }
    ipcPort = document.getElementById("cfg-network-ipc-port");
    if (ipcPort) {
        ipcPort.value = (window.systemConfig.network_ipc_port || 0);
    }
    webPort = document.getElementById("cfg-network-web-port");
    if (webPort) {
        webPort.value = (window.systemConfig.network_web_port || 0);
    }
    maxMsg = document.getElementById("cfg-network-max-message-size");
    if (maxMsg) {
        maxMsg.value = (window.systemConfig.network_max_message_size || 0);
    }
    seedAddr = document.getElementById("cfg-network-seed-addr");
    if (seedAddr) {
        seedAddr.value = (window.systemConfig.network_seed_addr || "");
    }
    seedPort = document.getElementById("cfg-network-seed-port");
    if (seedPort) {
        seedPort.value = (window.systemConfig.network_seed_port || 0);
    }
    raftPort = document.getElementById("cfg-consensus-raft-port");
    if (raftPort) {
        raftPort.value = (window.systemConfig.consensus_raft_port || 0);
    }
    electTimeout = document.getElementById("cfg-consensus-election-timeout");
    if (electTimeout) {
        electTimeout.value = (window.systemConfig.consensus_election_timeout_ms || 0);
    }
    heartbeat = document.getElementById("cfg-consensus-heartbeat-interval");
    if (heartbeat) {
        heartbeat.value = (window.systemConfig.consensus_heartbeat_interval_ms || 0);
    }
    rateLimit = document.getElementById("cfg-security-rate-limit");
    if (rateLimit) {
        rateLimit.value = (window.systemConfig.security_rate_limit_per_minute || 0);
    }
    banThresh = document.getElementById("cfg-security-ban-threshold");
    if (banThresh) {
        banThresh.value = (window.systemConfig.security_ban_threshold || 0);
    }
    banDur = document.getElementById("cfg-security-ban-duration");
    if (banDur) {
        banDur.value = (window.systemConfig.security_ban_duration_sec || 0);
    }
    enableHostElect = document.getElementById("cfg-network-enable-host-election");
    if (enableHostElect) {
        enableHostElect.checked = (window.systemConfig.network_enable_host_election === 1);
    }
    isStaticHost = document.getElementById("cfg-network-is-static-host");
    if (isStaticHost) {
        isStaticHost.checked = (window.systemConfig.network_is_static_host === 1);
    }
    return 0;
}

function showSystemConfigStatus(text, statusType) {
    let el;
    el = document.getElementById("settings-sys-status-msg");
    if (el) {
        el.textContent = text;
        el.className = "status-msg";
        if ((statusType === 1)) {
            el.classList.add("success");
        } else if ((statusType === 2)) {
            el.classList.add("warning");
        } else {
            el.classList.add("error");
        }
        setTimeout((dummy) => {
    el.textContent = "";
    el.className = "status-msg";
}, 5000);
    }
    return 0;
}

function saveSystemConfig() {
    let val, isStaticHost, valElect, enableHostElect, valStatic, payload;
    if ((!window.ws || !window.isConnected)) {
        showSystemConfigStatus("Error: Daemon disconnected.", 0);
        return 0;
    }
    window.systemConfig = Object();
    val = document.getElementById("cfg-node-name").value.trim();
    window.systemConfig.node_name = val;
    val = document.getElementById("cfg-node-log-level").value;
    window.systemConfig.node_log_level = val;
    val = document.getElementById("cfg-node-data-dir").value.trim();
    window.systemConfig.node_data_dir = val;
    val = document.getElementById("cfg-storage-max-content-size").value;
    window.systemConfig.storage_max_content_size = val;
    val = document.getElementById("cfg-storage-dht-ttl-sec").value;
    window.systemConfig.storage_dht_ttl_sec = val;
    val = document.getElementById("cfg-network-listen-address").value.trim();
    window.systemConfig.network_listen_address = val;
    val = document.getElementById("cfg-network-max-connections").value;
    window.systemConfig.network_max_connections = val;
    val = document.getElementById("cfg-network-p2p-port").value;
    window.systemConfig.network_p2p_port = val;
    val = document.getElementById("cfg-network-dht-port").value;
    window.systemConfig.network_dht_port = val;
    val = document.getElementById("cfg-network-relay-port").value;
    window.systemConfig.network_relay_port = val;
    val = document.getElementById("cfg-network-ipc-port").value;
    window.systemConfig.network_ipc_port = val;
    val = document.getElementById("cfg-network-web-port").value;
    window.systemConfig.network_web_port = val;
    val = document.getElementById("cfg-network-max-message-size").value;
    window.systemConfig.network_max_message_size = val;
    val = document.getElementById("cfg-network-seed-addr").value.trim();
    window.systemConfig.network_seed_addr = val;
    val = document.getElementById("cfg-network-seed-port").value;
    window.systemConfig.network_seed_port = val;
    val = document.getElementById("cfg-consensus-raft-port").value;
    window.systemConfig.consensus_raft_port = val;
    val = document.getElementById("cfg-consensus-election-timeout").value;
    window.systemConfig.consensus_election_timeout_ms = val;
    val = document.getElementById("cfg-consensus-heartbeat-interval").value;
    window.systemConfig.consensus_heartbeat_interval_ms = val;
    val = document.getElementById("cfg-security-rate-limit").value;
    window.systemConfig.security_rate_limit_per_minute = val;
    val = document.getElementById("cfg-security-ban-threshold").value;
    window.systemConfig.security_ban_threshold = val;
    val = document.getElementById("cfg-security-ban-duration").value;
    window.systemConfig.security_ban_duration_sec = val;
    valElect = 0;
    enableHostElect = document.getElementById("cfg-network-enable-host-election");
    if ((enableHostElect && enableHostElect.checked)) {
        valElect = 1;
    }
    window.systemConfig.network_enable_host_election = valElect;
    valStatic = 0;
    isStaticHost = document.getElementById("cfg-network-is-static-host");
    if ((isStaticHost && isStaticHost.checked)) {
        valStatic = 1;
    }
    window.systemConfig.network_is_static_host = valStatic;
    payload = Object();
    payload.type = "save_system_config";
    payload.data = JSON.stringify(window.systemConfig);
    send_msg(window.ws, JSON.stringify(payload));
    return 0;
}

function savePlatformConfig(platformId) {
    let chanVal, payload, tokenVal, enabledVal, discConfig, whatsappConfig, telegramConfig, phoneVal;
    if (((!window.platforms || !window.ws) || !window.isConnected)) {
        return 0;
    }
    if ((platformId === "discord")) {
        discConfig = window.platforms.discord;
        if (!discConfig) {
            discConfig = Object();
            window.platforms.discord = discConfig;
        }
        tokenVal = document.getElementById("overview-discord-token").value.trim();
        chanVal = document.getElementById("overview-discord-channel").value.trim();
        enabledVal = document.getElementById("toggle-discord").checked;
        discConfig.token = tokenVal;
        set_prop(discConfig, "channel", chanVal);
        discConfig.enabled = enabledVal;
        if (enabledVal) {
            discConfig.status = "ONLINE";
        } else {
            discConfig.status = "OFFLINE";
        }
    } else if ((platformId === "whatsapp")) {
        whatsappConfig = window.platforms.whatsapp;
        if (!whatsappConfig) {
            whatsappConfig = Object();
            window.platforms.whatsapp = whatsappConfig;
        }
        tokenVal = document.getElementById("overview-whatsapp-token").value.trim();
        phoneVal = document.getElementById("overview-whatsapp-phone-id").value.trim();
        enabledVal = document.getElementById("toggle-whatsapp").checked;
        whatsappConfig.token = tokenVal;
        whatsappConfig.phone_id = phoneVal;
        whatsappConfig.enabled = enabledVal;
        if (enabledVal) {
            whatsappConfig.status = "ONLINE";
        } else {
            whatsappConfig.status = "OFFLINE";
        }
    } else if ((platformId === "telegram")) {
        telegramConfig = window.platforms.telegram;
        if (!telegramConfig) {
            telegramConfig = Object();
            window.platforms.telegram = telegramConfig;
        }
        tokenVal = document.getElementById("overview-telegram-token").value.trim();
        enabledVal = document.getElementById("toggle-telegram").checked;
        telegramConfig.token = tokenVal;
        telegramConfig.enabled = enabledVal;
        if (enabledVal) {
            telegramConfig.status = "ONLINE";
        } else {
            telegramConfig.status = "OFFLINE";
        }
    }
    payload = Object();
    payload.type = "save_platforms";
    payload.data = JSON.stringify(window.platforms);
    send_msg(window.ws, JSON.stringify(payload));
    updatePlatformsUI();
    return 0;
}

function handlePlatformToggle(platformId) {
    let discConfig, enabledVal, payload, telegramConfig, whatsappConfig;
    if (((!window.platforms || !window.ws) || !window.isConnected)) {
        return 0;
    }
    if ((platformId === "discord")) {
        discConfig = window.platforms.discord;
        if (discConfig) {
            enabledVal = document.getElementById("toggle-discord").checked;
            discConfig.enabled = enabledVal;
            if (enabledVal) {
                discConfig.status = "ONLINE";
            } else {
                discConfig.status = "OFFLINE";
            }
        }
    } else if ((platformId === "whatsapp")) {
        whatsappConfig = window.platforms.whatsapp;
        if (whatsappConfig) {
            enabledVal = document.getElementById("toggle-whatsapp").checked;
            whatsappConfig.enabled = enabledVal;
            if (enabledVal) {
                whatsappConfig.status = "ONLINE";
            } else {
                whatsappConfig.status = "OFFLINE";
            }
        }
    } else if ((platformId === "telegram")) {
        telegramConfig = window.platforms.telegram;
        if (telegramConfig) {
            enabledVal = document.getElementById("toggle-telegram").checked;
            telegramConfig.enabled = enabledVal;
            if (enabledVal) {
                telegramConfig.status = "ONLINE";
            } else {
                telegramConfig.status = "OFFLINE";
            }
        }
    }
    payload = Object();
    payload.type = "save_platforms";
    payload.data = JSON.stringify(window.platforms);
    send_msg(window.ws, JSON.stringify(payload));
    updatePlatformsUI();
    return 0;
}

function registerPlugin() {
    let desc, name, endpoint, newPlugin;
    if (!window.plugins) {
        window.plugins = [];
    }
    name = prompt("Enter plugin name:", "");
    if ((!name || (name.trim().length === 0))) {
        return 0;
    }
    endpoint = prompt("Enter endpoint (URL or script name):", "");
    if ((!endpoint || (endpoint.trim().length === 0))) {
        return 0;
    }
    desc = prompt("Enter description:", "");
    if (!desc) {
        desc = "";
    }
    newPlugin = Object();
    newPlugin.id = ("plugin_" + Date.now());
    newPlugin.name = name.trim();
    newPlugin.endpoint = endpoint.trim();
    newPlugin.desc = desc.trim();
    newPlugin.enabled = true;
    newPlugin.status = "ACTIVE";
    window.plugins.push(newPlugin);
    savePluginsSettings();
    renderPluginsUI();
    return 0;
}

function updateSessionsUI(sessions) {
    let container;
    container = document.getElementById("ai-sessions-list-container");
    if (!container) {
        return 0;
    }
    container.innerHTML = "";
    if ((sessions.length === 0)) {
        container.innerHTML = "<div style=\"padding:10px;font-size:12px;color:rgba(255,255,255,0.4);text-align:center;\">No active sessions.</div>";
        return 0;
    }
    sessions.forEach((s) => {
    activeClass = "";
    if ((window.activeSessionId === s.id)) {
        activeClass = "active";
    }
    item = document.createElement("div");
    item.className = ("room-item " + String(activeClass));
    ok = set_prop(item.style, "display", "flex");
    item.style.justifyContent = "space-between";
    item.style.alignItems = "center";
    item.style.width = "100%";
    item.style.padding = "8px 12px";
    item.style.cursor = "pointer";
    item.style.marginBottom = "4px";
    item.style.borderRadius = "6px";
    item.addEventListener("click", (event) => {
    if ((event.target.closest(".btn-delete-session") || event.target.closest(".btn-rename-session"))) {
        return 0;
    }
    selectSession(s.id);
});
    labelSpan = document.createElement("span");
    labelSpan.className = "session-label";
    labelSpan.textContent = (s.title || s.id);
    labelSpan.style.overflow = "hidden";
    labelSpan.style.textOverflow = "ellipsis";
    labelSpan.style.whiteSpace = "nowrap";
    labelSpan.style.flex = "1";
    item.appendChild(labelSpan);
    actionsDiv = document.createElement("div");
    ok = set_prop(actionsDiv.style, "display", "flex");
    actionsDiv.style.gap = "6px";
    renameBtn = document.createElement("button");
    renameBtn.className = "btn-rename-session";
    renameBtn.innerHTML = "✏️";
    renameBtn.style.background = "none";
    renameBtn.style.border = "none";
    renameBtn.style.cursor = "pointer";
    renameBtn.style.padding = "0";
    renameBtn.style.fontSize = "11px";
    renameBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    newTitle = prompt("Enter new session title:", (s.title || s.id));
    if ((newTitle && (newTitle.trim().length > 0))) {
        renameSession(s.id, newTitle.trim());
    }
});
    actionsDiv.appendChild(renameBtn);
    deleteBtn = document.createElement("button");
    deleteBtn.className = "btn-delete-session";
    deleteBtn.innerHTML = "🗑️";
    deleteBtn.style.background = "none";
    deleteBtn.style.border = "none";
    deleteBtn.style.cursor = "pointer";
    deleteBtn.style.padding = "0";
    deleteBtn.style.fontSize = "11px";
    deleteBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    if (confirm((("Are you sure you want to delete session '" + String((s.title || s.id))) + "'?"))) {
        deleteSession(s.id);
    }
});
    actionsDiv.appendChild(deleteBtn);
    item.appendChild(actionsDiv);
    container.appendChild(item);
});
    return 0;
}

function initMemoryCanvas() {
    let height, width, canvas, oldCanvas, container, emptyState;
    container = document.getElementById("memory-graph-viz");
    if (!container) {
        return 0;
    }
    oldCanvas = container.querySelector("canvas");
    if (oldCanvas) {
        oldCanvas.remove();
    }
    canvas = document.createElement("canvas");
    width = (container.clientWidth || 600);
    height = (container.clientHeight || 400);
    canvas.width = width;
    canvas.height = height;
    set_prop(canvas.style, "display", "block");
    emptyState = container.querySelector(".empty-state");
    if (emptyState) {
        set_prop(emptyState.style, "display", "none");
    }
    container.appendChild(canvas);
    window.canvasElement = canvas;
    window.canvasCtx = canvas.getContext("2d");
    if (!window.animationFrameId) {
        animateGraph();
    }
}

function updateMemoryGraphData(edges) {
    let width, incomingNodes, height, currentIds;
    if (!window.canvasElement) {
        initMemoryCanvas();
    }
    if (!window.canvasElement) {
        return 0;
    }
    width = window.canvasElement.width;
    height = window.canvasElement.height;
    incomingNodes = Reflect.construct(window["Set"], []);
    edges.forEach((e) => {
    incomingNodes.add(e.source);
    incomingNodes.add(e.target);
});
    incomingNodes.forEach((id) => {
    hasNode = Reflect.has(window.graphNodes, id);
    if (!hasNode) {
        node = Object();
        node.x = ((width / 2) + ((Math.random() - 0.5) * 160));
        node.y = ((height / 2) + ((Math.random() - 0.5) * 160));
        node.vx = 0;
        node.vy = 0;
        node.label = id;
        set_prop(window.graphNodes, id, node);
    }
});
    currentIds = Object.keys(window.graphNodes);
    currentIds.forEach((id) => {
    hasIncoming = incomingNodes.has(id);
    if (!hasIncoming) {
        Reflect.deleteProperty(window.graphNodes, id);
    }
});
    window.graphLinks = edges;
}

function animateGraph() {
    let j, n1, width, dist, height, fy, n2, nodeIds, dx, force, i, fx, dy;
    if (!window.isConnected) {
        window.animationFrameId = requestAnimationFrame((dummy) => {
    animateGraph();
});
        return 0;
    }
    if ((!window.canvasElement || !window.canvasCtx)) {
        window.animationFrameId = requestAnimationFrame((dummy) => {
    animateGraph();
});
        return 0;
    }
    width = window.canvasElement.width;
    height = window.canvasElement.height;
    nodeIds = Object.keys(window.graphNodes);
    i = 0;
    while ((i < nodeIds.length)) {
        j = (i + 1);
        while ((j < nodeIds.length)) {
            n1 = window.graphNodes[nodeIds[i]];
            n2 = window.graphNodes[nodeIds[j]];
            dx = (n2.x - n1.x);
            dy = (n2.y - n1.y);
            dist = (Math.hypot(dx, dy) || 1);
            force = (180 / (dist * dist));
            fx = ((dx / dist) * force);
            fy = ((dy / dist) * force);
            n1.vx = (n1.vx - fx);
            n1.vy = (n1.vy - fy);
            n2.vx = (n2.vx + fx);
            n2.vy = (n2.vy + fy);
            j = (j + 1);
        }
        i = (i + 1);
    }
    window.graphLinks.forEach((link) => {
    n1 = window.graphNodes[link.source];
    n2 = window.graphNodes[link.target];
    if ((n1 && n2)) {
        dx = (n2.x - n1.x);
        dy = (n2.y - n1.y);
        dist = (Math.hypot(dx, dy) || 1);
        force = (((dist - 130) * 0.06) * Math.min(link.weight, 1));
        fx = ((dx / dist) * force);
        fy = ((dy / dist) * force);
        n1.vx = (n1.vx + fx);
        n1.vy = (n1.vy + fy);
        n2.vx = (n2.vx - fx);
        n2.vy = (n2.vy - fy);
    }
});
    nodeIds.forEach((id) => {
    n = window.graphNodes[id];
    n.vx = (n.vx + (((width / 2) - n.x) * 0.015));
    n.vy = (n.vy + (((height / 2) - n.y) * 0.015));
    n.x = (n.x + n.vx);
    n.y = (n.y + n.vy);
    n.vx = (n.vx * 0.75);
    n.vy = (n.vy * 0.75);
    n.x = Math.max(24, Math.min((width - 24), n.x));
    n.y = Math.max(24, Math.min((height - 24), n.y));
});
    window.canvasCtx.clearRect(0, 0, width, height);
    window.graphLinks.forEach((link) => {
    n1 = window.graphNodes[link.source];
    n2 = window.graphNodes[link.target];
    if ((n1 && n2)) {
        window.canvasCtx.beginPath();
        window.canvasCtx.moveTo(n1.x, n1.y);
        window.canvasCtx.lineTo(n2.x, n2.y);
        window.canvasCtx.strokeStyle = (("rgba(6, 182, 212, " + String((0.15 + (link.weight * 0.75)))) + ")");
        window.canvasCtx.lineWidth = (1 + (link.weight * 4));
        window.canvasCtx.stroke();
        mx = ((n1.x + n2.x) / 2);
        my = ((n1.y + n2.y) / 2);
        window.canvasCtx.fillStyle = "rgba(156, 163, 175, 0.8)";
        window.canvasCtx.font = "9px 'JetBrains Mono', monospace";
        window.canvasCtx.fillText(link.weight.toFixed(3), (mx + 5), (my + 3));
    }
});
    nodeIds.forEach((id) => {
    n = window.graphNodes[id];
    window.canvasCtx.beginPath();
    window.canvasCtx.arc(n.x, n.y, 22, 0, (2 * Math.PI));
    window.canvasCtx.fillStyle = "rgba(168, 85, 247, 0.08)";
    window.canvasCtx.fill();
    window.canvasCtx.strokeStyle = "rgba(168, 85, 247, 0.25)";
    window.canvasCtx.lineWidth = 1;
    window.canvasCtx.stroke();
    window.canvasCtx.beginPath();
    window.canvasCtx.arc(n.x, n.y, 14, 0, (2 * Math.PI));
    window.canvasCtx.fillStyle = "#0c0e17";
    window.canvasCtx.fill();
    window.canvasCtx.strokeStyle = "#a855f7";
    window.canvasCtx.lineWidth = 2;
    window.canvasCtx.stroke();
    window.canvasCtx.fillStyle = "#ffffff";
    window.canvasCtx.font = "12px 'Outfit', sans-serif";
    window.canvasCtx.textAlign = "center";
    window.canvasCtx.fillText(n.label, n.x, (n.y + 4));
});
    window.animationFrameId = requestAnimationFrame((dummy) => {
    animateGraph();
});
}

function renderTuringGrid(data) {
    let isHead, headX, c, turingHeadPos, headZ, r, cellClass, html, headY, value, turingCellsCount, container, cellKey;
    container = document.getElementById("turing-grid-viz");
    if (!container) {
        return 0;
    }
    headX = data.x;
    headY = data.y;
    headZ = data.z;
    html = (("<div class=\"grid-layer-title\">Layer Z = " + String(escapeHTML(headZ))) + "</div>");
    html = (html + "<table class=\"turing-table\">");
    r = (headY - 3);
    while ((r <= (headY + 3))) {
        html = (html + "<tr>");
        c = (headX - 3);
        while ((c <= (headX + 3))) {
            cellKey = ((((String(c) + "_") + String(r)) + "_") + String(headZ));
            value = (data.cells[cellKey] || "");
            isHead = 0;
            if (((c === headX) && (r === headY))) {
                isHead = 1;
            }
            cellClass = "";
            if ((isHead === 1)) {
                cellClass = "head-cell";
            }
            if ((value !== "")) {
                cellClass = (cellClass + " active-cell");
            }
            html = (html + (((((((((((((("<td class=\"" + String(cellClass)) + "\" title=\"Coord: (") + String(c)) + ", ") + String(r)) + ", ") + String(escapeHTML(headZ))) + ")\"><span class=\"coord\">(") + String(c)) + ",") + String(r)) + ")</span><span class=\"val\">") + String(escapeHTML(value))) + "</span>"));
            if ((isHead === 1)) {
                html = (html + "<span class=\"head-marker\">▲ HEAD</span>");
            }
            html = (html + "</td>");
            c = (c + 1);
        }
        html = (html + "</tr>");
        r = (r + 1);
    }
    html = (html + "</table>");
    container.innerHTML = html;
    turingHeadPos = document.getElementById("turing-head-pos");
    turingHeadPos.textContent = (((((("(" + String(headX)) + ", ") + String(headY)) + ", ") + String(headZ)) + ")");
    turingCellsCount = document.getElementById("turing-cells-count");
    turingCellsCount.textContent = Object.keys(data.cells).length;
}

function updateMemoryTables(data) {
    let sBody, lBody, keys;
    sBody = document.getElementById("scratchpad-body");
    if (sBody) {
        sBody.innerHTML = "";
        keys = Object.keys(data.scratchpad);
        if ((keys.length === 0)) {
            sBody.innerHTML = "<tr><td colspan=\"2\" class=\"empty-state\">Empty</td></tr>";
        } else {
            keys.forEach((k) => {
    row = document.createElement("tr");
    v = data.scratchpad[k];
    row.innerHTML = (((("<td><code>" + String(escapeHTML(k))) + "</code></td><td>") + String(escapeHTML(v))) + "</td>");
    sBody.appendChild(row);
});
        }
    }
    lBody = document.getElementById("lessons-body");
    if (lBody) {
        lBody.innerHTML = "";
        keys = Object.keys(data.lessons);
        if ((keys.length === 0)) {
            lBody.innerHTML = "<tr><td colspan=\"2\" class=\"empty-state\">Empty</td></tr>";
        } else {
            keys.forEach((k) => {
    row = document.createElement("tr");
    v = data.lessons[k];
    row.innerHTML = (((("<td><code>" + String(escapeHTML(k))) + "</code></td><td>") + String(escapeHTML(v))) + "</td>");
    lBody.appendChild(row);
});
        }
    }
}

function handleDaemonMessage(msg) {
    let sigKeyEl, encKeyEl, rvRepos, sess, bwDown, timeStrSec, uiHostElect, summaryNotice, nodeTerm, rvFile, sess_id, didFull, auToggle, activeCircuits, dateStr, ttsAudio, timeParts, dhtSize, bwUp, computeSlots, secParts, uiStaticHost, chunkCount, msgSessions, nodePeers, gdBadge, type, roleUpper, walletVal, textNode, timeStr, idNameEl, stopBtn, noSelected, detailsPanel, btnSubmit, headerDid, nodeRole, refresh, nameInput, storageBody, natMode, aiText;
    type = msg.type;
    if ((type === "status")) {
        roleUpper = msg.role.toUpperCase();
        nodeRole = document.getElementById("node-role");
        nodeRole.textContent = roleUpper;
        nodeTerm = document.getElementById("node-term");
        nodeTerm.textContent = (("Term " + String(msg.term)) + " (Raft)");
        headerDid = document.getElementById("header-did");
        if ((msg.name && (msg.name !== "none"))) {
            headerDid.textContent = msg.name;
        } else {
            headerDid.textContent = (substring(msg.did, 0, 15) + "...");
        }
        didFull = document.getElementById("did-full-string");
        didFull.textContent = msg.did;
        window.localIdentityDid = msg.did;
        nodePeers = document.getElementById("node-peers");
        nodePeers.textContent = msg.peers;
        dhtSize = document.getElementById("dht-size");
        dhtSize.textContent = (String(msg.dht_size) + " entries");
        gdBadge = document.getElementById("gitdec-update-badge");
        if (gdBadge) {
            if ((msg.gitdec_updates && (msg.gitdec_updates > 0))) {
                gdBadge.textContent = msg.gitdec_updates;
                set_prop(gdBadge.style, "display", "inline-block");
            } else {
                set_prop(gdBadge.style, "display", "none");
            }
        }
        uiHostElect = document.getElementById("ui-host-election-status");
        if (uiHostElect) {
            if ((msg.enable_host_election === 1)) {
                uiHostElect.textContent = "Enabled";
                set_prop(uiHostElect.style, "color", "var(--neon-cyan)");
            } else {
                uiHostElect.textContent = "Disabled";
                set_prop(uiHostElect.style, "color", "var(--text-muted)");
            }
        }
        uiStaticHost = document.getElementById("ui-static-host-status");
        if (uiStaticHost) {
            if ((msg.is_static_host === 1)) {
                uiStaticHost.textContent = "Active (Host Node)";
                set_prop(uiStaticHost.style, "color", "var(--neon-purple)");
            } else {
                uiStaticHost.textContent = "Inactive";
                set_prop(uiStaticHost.style, "color", "var(--text-muted)");
            }
        }
    } else if ((type === "identity")) {
        didFull = document.getElementById("did-full-string");
        didFull.textContent = msg.did;
        window.localIdentityDid = msg.did;
        idNameEl = document.getElementById("identity-registered-name");
        if (idNameEl) {
            if ((msg.name && (msg.name !== "none"))) {
                idNameEl.textContent = msg.name;
                nameInput = document.getElementById("name-input");
                if ((nameInput && !nameInput.value)) {
                    nameInput.value = msg.name;
                }
            } else {
                idNameEl.textContent = "Not Registered";
            }
        }
        sigKeyEl = document.getElementById("signing-key-display");
        encKeyEl = document.getElementById("encryption-key-display");
        if (sigKeyEl) {
            sigKeyEl.textContent = (msg.signing_key || "—");
        }
        if (encKeyEl) {
            encKeyEl.textContent = (msg.encryption_key || "—");
        }
    } else if ((type === "wallet")) {
        walletVal = document.getElementById("wallet-val");
        walletVal.textContent = parseFloat(msg.balance).toFixed(2);
    } else if ((type === "storage")) {
        chunkCount = document.getElementById("chunk-count");
        chunkCount.textContent = msg.chunk_count;
        storageBody = document.getElementById("storage-files-body");
        if (storageBody) {
            storageBody.innerHTML = "";
            if ((!msg.files || (msg.files.length === 0))) {
                storageBody.innerHTML = "<tr><td colspan=\"4\" class=\"empty-state\">No content blocks stored.</td></tr>";
            } else {
                msg.files.forEach((f) => {
    row = document.createElement("tr");
    row.innerHTML = (((((((("<td><code>" + String(escapeHTML(f.name))) + "</code></td><td><code class=\"small-code\">") + String(escapeHTML(f.hash))) + "</code></td><td>") + String(escapeHTML(f.size))) + "</td><td><span class=\"badge badge-green\">") + String(escapeHTML(f.type))) + "</span></td>");
    storageBody.appendChild(row);
});
            }
        }
    } else if ((type === "pool")) {
        bwUp = document.getElementById("bandwidth-up");
        bwDown = document.getElementById("bandwidth-down");
        computeSlots = document.getElementById("compute-slots");
        if (bwUp) {
            bwUp.textContent = (msg.bandwidth_up || "0");
        }
        if (bwDown) {
            bwDown.textContent = (msg.bandwidth_down || "0");
        }
        if (computeSlots) {
            computeSlots.textContent = (msg.compute_slots || "0");
        }
    } else if ((type === "network")) {
        natMode = document.getElementById("nat-mode");
        activeCircuits = document.getElementById("active-circuits");
        if (natMode) {
            natMode.textContent = (msg.nat_mode || "relay");
        }
        if (activeCircuits) {
            activeCircuits.textContent = (msg.active_circuits || "0");
        }
    } else if ((type === "chat_msg")) {
        appendMessage(window.chatContainer, msg.sender, msg.text, "received");
    } else if ((type === "ai_token")) {
        appendAiToken(msg.token);
    } else if ((type === "tool_pending_approval")) {
        appendApprovalCard(msg.tool, msg.summary);
    } else if ((type === "clarify")) {
        appendClarifyCard(msg.questions);
    } else if ((type === "reasoning")) {
        appendReasoningBubble(msg.b64);
    } else if ((type === "ai_complete")) {
        if (window.currentAiResponseBubble) {
            textNode = window.currentAiResponseBubble.querySelector(".ai-text");
            if (textNode) {
                aiText = textNode.textContent;
                dateStr = Date();
                timeParts = dateStr.split(" ");
                timeStrSec = timeParts[4];
                secParts = timeStrSec.split(":");
                timeStr = (secParts[0] + (":" + secParts[1]));
                saveAiMessage("AI (Local Model)", aiText, "received", timeStr);
                attachTtsButton(window.currentAiResponseBubble, aiText);
            }
        }
        set_prop(window.aiLoader.style, "display", "none");
        window.aiInput.disabled = false;
        btnSubmit = document.getElementById("btn-submit-ai");
        btnSubmit.disabled = false;
        stopBtn = document.getElementById("btn-stop-ai");
        if ((stopBtn !== 0)) {
            set_prop(stopBtn.style, "display", "none");
        }
        window.currentAiResponseBubble = null;
    } else if ((type === "tts_ready")) {
        if (window.pendingTtsBtn) {
            set_prop(window.pendingTtsBtn, "disabled", false);
            window.pendingTtsBtn.textContent = "🔊";
        }
        window.pendingTtsBtn = null;
        ttsAudio = document.createElement("audio");
        ttsAudio.src = msg.url;
        ttsAudio.play();
    } else if ((type === "tts_error")) {
        if (window.pendingTtsBtn) {
            set_prop(window.pendingTtsBtn, "disabled", false);
            window.pendingTtsBtn.textContent = "🔇";
        }
        window.pendingTtsBtn = null;
        console.error(("TTS error: " + msg.error));
    } else if ((type === "ai_models")) {
        updateAiModelsUI((msg.models || []));
    } else if ((type === "agent_memory")) {
        updateMemoryGraphData((msg.edges || []));
        updateMemoryTables(msg);
    } else if ((type === "turing_grid")) {
        renderTuringGrid(msg);
    } else if ((type === "platforms")) {
        window.platforms = msg.data;
        updatePlatformsUI();
    } else if ((type === "plugins")) {
        window.plugins = (msg.data || []);
        renderPluginsUI();
    } else if (((type === "platforms_saved") || (type === "plugins_saved"))) {
        console.log(("Daemon successfully saved configuration: " + String(type)));
    } else if ((type === "prompts")) {
        window.prompts = msg.data;
        updatePromptsUI();
    } else if ((type === "prompts_saved")) {
        showPromptsStatus("Settings saved successfully!", 1);
    } else if ((type === "system_config")) {
        window.systemConfig = msg.data;
        updateSystemConfigUI();
    } else if ((type === "system_config_saved")) {
        showSystemConfigStatus("Configuration saved! Restart daemon to apply network changes.", 2);
    } else if ((type === "error")) {
        console.error(("Daemon error: " + String(msg.message)));
    } else if ((type === "swap_result")) {
        if (!msg.success) {
            appendMessage(window.chatContainer, "system", ("Swap failed: " + String(msg.reason)), "received");
        }
    } else if ((type === "dht_result")) {
        handleDhtResult(msg);
    } else if ((type === "name_result")) {
        handleNameResult(msg);
    } else if ((type === "session_list")) {
        updateSessionsUI((msg.sessions || []));
    } else if (((type === "session_active") || (type === "session_details"))) {
        sess = msg.session;
        window.activeSessionId = sess.id;
        window.aiSystemPrompt.value = (sess.system_prompt || "You are a local assistant operating privately inside the ErnosDecent mesh.");
        selectAiModel((sess.model || ""), true);
        window.aiContainer.innerHTML = "";
        if ((!sess.messages || (sess.messages.length === 0))) {
            appendMessageRaw(window.aiContainer, "AI (Local Model)", "Greetings! I am loaded inside the decent_ai subsystem. My weights are decoded using Float32 fixed-point attention queries. Ask me anything.", "received", "00:00");
        } else {
            sess.messages.forEach((m) => {
    senderLabel = "AI (Local Model)";
    msgType = "received";
    if ((m.role === "user")) {
        senderLabel = "You";
        msgType = "sent";
    }
    appendMessageRaw(window.aiContainer, senderLabel, m.content, msgType, "00:00");
});
        }
        if ((sess.compression_summary && (sess.compression_summary.length > 0))) {
            summaryNotice = ("ℹ️ [CONTEXT COMPRESSED]\nSummary of prior conversation: " + String(sess.compression_summary));
            appendMessageRaw(window.aiContainer, "system", summaryNotice, "received", "00:00");
        }
        msgSessions = Object();
        msgSessions.type = "session_list";
        send_msg(window.ws, JSON.stringify(msgSessions));
    } else if ((type === "session_active_id")) {
        sess_id = msg.id;
        window.activeSessionId = sess_id;
        selectSession(sess_id);
    } else if ((type === "session_new_result")) {
        if (msg.success) {
            selectSession(msg.id);
        }
    } else if (((type === "session_rename_result") || (type === "session_delete_result"))) {
        msgSessions = Object();
        msgSessions.type = "session_list";
        send_msg(window.ws, JSON.stringify(msgSessions));
        if (((type === "session_delete_result") && (window.activeSessionId === msg.id))) {
            selectSession("default");
        }
    } else if ((type === "onion_result")) {
        handleOnionResult(msg);
    } else if ((type === "onion_view_result")) {
        handleOnionViewResult(msg);
    } else if ((type === "gitdec_repos")) {
        updateGitDecRepos(msg.repos);
    } else if ((type === "gitdec_visibility_ok")) {
        rvRepos = Object();
        rvRepos.type = "gitdec_get_repos";
        send_msg(window.ws, JSON.stringify(rvRepos));
        if (window.gitdecActiveRepo) {
            rvFile = Object();
            rvFile.type = "gitdec_get_repo_file";
            rvFile.repo_id = window.gitdecActiveRepo;
            rvFile.filename = "gitdec.json";
            send_msg(window.ws, JSON.stringify(rvFile));
        }
    } else if ((type === "gitdec_visibility_error")) {
        alert((msg.message || "Could not change visibility"));
    } else if ((type === "gitdec_auto_update_state")) {
        auToggle = document.getElementById("gitdec-settings-autoupdate-toggle");
        if (auToggle) {
            auToggle.checked = (msg.enabled === 1);
        }
    } else if ((type === "gitdec_merge_ok")) {
        alert("Merged to main and broadcast to the network.");
        refresh = Object();
        refresh.type = "gitdec_get_repos";
        send_msg(window.ws, JSON.stringify(refresh));
    } else if ((type === "gitdec_merge_error")) {
        alert(msg.message);
    } else if ((type === "gitdec_file")) {
        handleGitDecFile(msg.repo_id, msg.filename, msg.content);
    } else if ((type === "gitdec_files")) {
        renderGitDecFiles(msg.repo_id, msg.files);
    } else if ((type === "gitdec_delete_ok")) {
        alert("Repository deleted successfully!");
        window.gitdecActiveRepo = null;
        noSelected = document.getElementById("gitdec-no-repo-selected");
        detailsPanel = document.getElementById("gitdec-repo-details");
        set_prop(noSelected.style, "display", "block");
        set_prop(detailsPanel.style, "display", "none");
        refresh = Object();
        refresh.type = "gitdec_get_repos";
        send_msg(window.ws, JSON.stringify(refresh));
    } else if ((type === "gitdec_delete_error")) {
        alert(("Error deleting repository: " + (msg.message || "Unauthorized")));
    } else if ((type === "gitdec_collab_ok")) {
        refresh = Object();
        refresh.type = "gitdec_get_repo_file";
        refresh.repo_id = window.gitdecActiveRepo;
        refresh.filename = "gitdec.json";
        send_msg(window.ws, JSON.stringify(refresh));
    } else if ((type === "gitdec_collab_error")) {
        alert(("Collaborator error: " + (msg.message || "Unauthorized")));
    }
}

function handleOnionResult(msg) {
    let html, resultsBox, results;
    resultsBox = document.getElementById("onion-results-box");
    if (!resultsBox) {
        return 0;
    }
    results = msg.results;
    if ((!results || (results.length === 0))) {
        resultsBox.innerHTML = "<div style='color: var(--text-muted); text-align: center; padding: 20px 0;'>No results found.</div>";
        return 0;
    }
    html = "";
    results.forEach((r) => {
    decodedTitle = decodeHTMLEntities(r.title);
    decodedSnippet = decodeHTMLEntities(r.snippet);
    escTitle = escapeHTML(decodedTitle);
    escUrl = escapeHTML(r.url);
    escSnippet = escapeHTML(decodedSnippet);
    html = (html + (((((((("<div class=\"search-result-item\"><a class=\"search-result-title\" onclick=\"window.onionViewPage('" + String(r.url)) + "')\">") + String(escTitle)) + "</a><span class=\"search-result-url\">") + String(escUrl)) + "</span><p class=\"search-result-snippet\">") + String(escSnippet)) + "</p></div>"));
});
    resultsBox.innerHTML = html;
    return 0;
}

function getActiveTab() {
    let activeTab;
    activeTab = null;
    window.browserTabs.forEach((t) => {
    if ((t.id === window.activeTabId)) {
        activeTab = t;
    }
});
    return activeTab;
}

function createBrowserTab(url, activate) {
    let id, tab;
    id = ("tab_" + Math.random().toString(36).substring(2, 9));
    tab = Object();
    tab.id = id;
    tab.url = url;
    tab.title = "New Tab";
    tab.html = "";
    tab.history = [url];
    tab.historyIndex = 0;
    tab.loading = false;
    window.browserTabs.push(tab);
    if (activate) {
        window.activeTabId = id;
    }
    renderBrowserTabs();
    if ((url === "ernos://newtab")) {
        renderNewTabPage(tab);
    } else {
        navigateTab(tab, url);
    }
    return 0;
}

function renderBrowserTabs() {
    let tabbar;
    tabbar = document.getElementById("browser-tabbar");
    if (!tabbar) {
        return 0;
    }
    tabbar.innerHTML = "";
    window.browserTabs.forEach((tab) => {
    tabEl = document.createElement("div");
    tabEl.className = "browser-tab";
    if ((tab.id === window.activeTabId)) {
        tabEl.classList.add("active");
    }
    iconSpan = document.createElement("span");
    iconSpan.className = "browser-tab-icon";
    if (tab.loading) {
        iconSpan.innerHTML = "<div class='modal-spinner' style='width:12px; height:12px; border-width:2px; border-top-color:var(--neon-cyan); margin:0;'></div>";
    } else if ((tab.url === "ernos://newtab")) {
        iconSpan.textContent = "🌱";
    } else {
        iconSpan.textContent = "🌱";
    }
    titleSpan = document.createElement("span");
    titleSpan.className = "browser-tab-title";
    titleSpan.textContent = tab.title;
    closeBtn = document.createElement("span");
    closeBtn.className = "browser-tab-close";
    closeBtn.innerHTML = "&times;";
    closeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    closeBrowserTab(tab.id);
});
    tabEl.appendChild(iconSpan);
    tabEl.appendChild(titleSpan);
    tabEl.appendChild(closeBtn);
    tabEl.addEventListener("click", (e) => {
    switchBrowserTab(tab.id);
});
    tabbar.appendChild(tabEl);
});
    return 0;
}

function switchBrowserTab(tabId) {
    let tab, contentArea, addressInput, loader;
    window.activeTabId = tabId;
    renderBrowserTabs();
    tab = null;
    window.browserTabs.forEach((t) => {
    if ((t.id === tabId)) {
        tab = t;
    }
});
    if (!tab) {
        return 0;
    }
    addressInput = document.getElementById("browser-address-input");
    if (addressInput) {
        if ((tab.url === "ernos://newtab")) {
            addressInput.value = "";
        } else {
            addressInput.value = tab.url;
        }
    }
    contentArea = document.getElementById("reader-modal-content");
    loader = document.getElementById("reader-modal-loader");
    if (tab.loading) {
        set_prop(loader.style, "display", "flex");
        set_prop(contentArea.style, "display", "none");
    } else {
        set_prop(loader.style, "display", "none");
        set_prop(contentArea.style, "display", "block");
        if ((tab.url === "ernos://newtab")) {
            renderNewTabPage(tab);
        } else {
            set_prop(contentArea, "innerHTML", tab.html);
            interceptViewportClicks();
        }
    }
    updateNavButtons(tab);
    updateStarButton(tab);
    return 0;
}

function closeBrowserTab(tabId) {
    let i, idx, tObj, modal;
    idx = (0 - 1);
    i = 0;
    window.browserTabs.forEach((t) => {
    if ((t.id === tabId)) {
        idx = i;
    }
    i = (i + 1);
});
    if ((idx === (0 - 1))) {
        return 0;
    }
    window.browserTabs.splice(idx, 1);
    if ((window.browserTabs.length === 0)) {
        modal = document.getElementById("reader-view-modal");
        modal.classList.remove("active");
        return 0;
    }
    if ((window.activeTabId === tabId)) {
        if ((idx < window.browserTabs.length)) {
            tObj = Reflect.get(window.browserTabs, idx);
            window.activeTabId = tObj.id;
        } else {
            tObj = Reflect.get(window.browserTabs, (window.browserTabs.length - 1));
            window.activeTabId = tObj.id;
        }
    }
    switchBrowserTab(window.activeTabId);
    return 0;
}

function navigateTab(tab, url) {
    let isSearch, contentArea, targetUrl, addressInput, progressBar, hasDot, viewMsg, hasProtocol, loader;
    targetUrl = url.trim();
    if ((targetUrl === "")) {
        return 0;
    }
    isSearch = false;
    if ((string_index_of(targetUrl, " ") >= 0)) {
        isSearch = true;
    } else {
        hasProtocol = false;
        if ((string_index_of(targetUrl, "://") >= 0)) {
            hasProtocol = true;
        }
        hasDot = false;
        if ((string_index_of(targetUrl, ".") >= 0)) {
            hasDot = true;
        }
        if ((!hasProtocol && !hasDot)) {
            isSearch = true;
        }
    }
    if (isSearch) {
        targetUrl = ("https://html.duckduckgo.com/html/?q=" + encodeURIComponent(targetUrl));
    } else if ((string_index_of(targetUrl, "://") < 0)) {
        targetUrl = ("https://" + targetUrl);
    }
    tab.url = targetUrl;
    tab.loading = true;
    tab.title = targetUrl;
    if ((tab.id === window.activeTabId)) {
        addressInput = document.getElementById("browser-address-input");
        if (addressInput) {
            addressInput.value = targetUrl;
        }
        loader = document.getElementById("reader-modal-loader");
        contentArea = document.getElementById("reader-modal-content");
        set_prop(loader.style, "display", "flex");
        set_prop(contentArea.style, "display", "none");
        progressBar = document.getElementById("browser-progress-bar");
        if (progressBar) {
            set_prop(progressBar.style, "width", "30%");
        }
        renderBrowserTabs();
    }
    viewMsg = Object();
    viewMsg.type = "onion_view";
    viewMsg.url = targetUrl;
    viewMsg.tabId = tab.id;
    send_msg(window.ws, JSON.stringify(viewMsg));
    return 0;
}

function navigateActiveTab(url, isHistoryNavigation) {
    let activeTab;
    activeTab = getActiveTab();
    if (!activeTab) {
        return 0;
    }
    if (!isHistoryNavigation) {
        activeTab.history = activeTab.history.slice(0, (activeTab.historyIndex + 1));
        activeTab.history.push(url);
        activeTab.historyIndex = (activeTab.history.length - 1);
    }
    navigateTab(activeTab, url);
    return 0;
}

function updateNavButtons(tab) {
    let btnBack, btnForward;
    btnBack = document.getElementById("btn-browser-back");
    if (btnBack) {
        btnBack.disabled = (tab.historyIndex <= 0);
    }
    btnForward = document.getElementById("btn-browser-forward");
    if (btnForward) {
        btnForward.disabled = (tab.historyIndex >= (tab.history.length - 1));
    }
    return 0;
}

function updateStarButton(tab) {
    let btnStar, isBookmarked;
    btnStar = document.getElementById("btn-browser-star");
    if (!btnStar) {
        return 0;
    }
    if ((tab.url === "ernos://newtab")) {
        set_prop(btnStar.style, "display", "none");
        return 0;
    }
    set_prop(btnStar.style, "display", "block");
    isBookmarked = false;
    window.browserBookmarks.forEach((b) => {
    if ((b.url === tab.url)) {
        isBookmarked = true;
    }
});
    if (isBookmarked) {
        btnStar.classList.add("active");
        btnStar.textContent = "\\u2605";
    } else {
        btnStar.classList.remove("active");
        btnStar.textContent = "\\u2606";
    }
    return 0;
}

function toggleBookmarkActiveTab() {
    let activeTab, existingIdx, newBookmark, i;
    activeTab = getActiveTab();
    if ((!activeTab || (activeTab.url === "ernos://newtab"))) {
        return 0;
    }
    existingIdx = (0 - 1);
    i = 0;
    window.browserBookmarks.forEach((b) => {
    if ((b.url === activeTab.url)) {
        existingIdx = i;
    }
    i = (i + 1);
});
    if ((existingIdx >= 0)) {
        window.browserBookmarks.splice(existingIdx, 1);
    } else {
        newBookmark = Object();
        newBookmark.title = activeTab.title;
        newBookmark.url = activeTab.url;
        window.browserBookmarks.push(newBookmark);
    }
    renderBookmarksBar();
    updateStarButton(activeTab);
    return 0;
}

function renderBookmarksBar() {
    let bar, homeItem;
    bar = document.getElementById("browser-bookmarks-bar");
    if (!bar) {
        return 0;
    }
    bar.innerHTML = "";
    homeItem = document.createElement("div");
    homeItem.className = "browser-bookmark-item";
    homeItem.innerHTML = "🌱 Ernos Home";
    homeItem.addEventListener("click", (event) => {
    navigateActiveTab("ernos://newtab", false);
});
    bar.appendChild(homeItem);
    window.browserBookmarks.forEach((b) => {
    item = document.createElement("div");
    item.className = "browser-bookmark-item";
    shortTitle = b.title;
    if ((shortTitle.length > 20)) {
        shortTitle = (shortTitle.substring(0, 17) + "...");
    }
    item.textContent = ("🔖 " + shortTitle);
    item.title = b.url;
    item.addEventListener("click", (event) => {
    navigateActiveTab(b.url, false);
});
    bar.appendChild(item);
});
    return 0;
}

function resolveRelativeUrl(baseUrl, relativeUrl) {
    let domain, protoIdx, baseFolder, afterProto, lastSlash, firstSlash;
    if (((string_index_of(relativeUrl, "://") >= 0) || (string_index_of(relativeUrl, "data:") === 0))) {
        return relativeUrl;
    }
    if ((string_index_of(relativeUrl, "/") === 0)) {
        protoIdx = string_index_of(baseUrl, "://");
        if ((protoIdx >= 0)) {
            afterProto = (protoIdx + 3);
            firstSlash = baseUrl.indexOf("/", afterProto);
            if ((firstSlash >= 0)) {
                domain = baseUrl.substring(0, firstSlash);
                return (domain + relativeUrl);
            } else {
                return (baseUrl + relativeUrl);
            }
        } else {
            return relativeUrl;
        }
    }
    lastSlash = baseUrl.lastIndexOf("/");
    protoIdx = string_index_of(baseUrl, "://");
    if ((lastSlash <= (protoIdx + 2))) {
        return ((baseUrl + "/") + relativeUrl);
    }
    baseFolder = baseUrl.substring(0, (lastSlash + 1));
    return (baseFolder + relativeUrl);
}

function interceptViewportClicks() {
    let contentArea, links;
    contentArea = document.getElementById("reader-modal-content");
    if (!contentArea) {
        return 0;
    }
    links = contentArea.querySelectorAll("a");
    links.forEach((aLink) => {
    aLink.addEventListener("click", (event) => {
    event.preventDefault();
    href = aLink.getAttribute("href");
    if (href) {
        activeTab = getActiveTab();
        absoluteUrl = resolveRelativeUrl(activeTab.url, href);
        navigateActiveTab(absoluteUrl, false);
    }
});
});
    return 0;
}

function renderNewTabPage(tab) {
    let scGithub, scDdg, newTabHtml, scTor, form, scWiki, contentArea;
    contentArea = document.getElementById("reader-modal-content");
    if ((tab.id !== window.activeTabId)) {
        return 0;
    }
    newTabHtml = "<div class=\"newtab-container\"><div class=\"newtab-logo\">&#x1F331;</div><div class=\"newtab-title\">Ernos Private Browser</div><div class=\"newtab-search-box\"><form id=\"newtab-search-form\" class=\"newtab-search-form\" onsubmit=\"return false;\"><input type=\"text\" id=\"newtab-search-input\" class=\"newtab-search-input\" placeholder=\"Search privately with DuckDuckGo or enter URL...\" required><button type=\"submit\" class=\"newtab-search-btn\">Search</button></form></div><div class=\"newtab-grid\"><div class=\"newtab-shortcut\" id=\"shortcut-ddg\"><span class=\"newtab-shortcut-icon\">&#x1F50D;</span><span class=\"newtab-shortcut-title\">DuckDuckGo</span></div><div class=\"newtab-shortcut\" id=\"shortcut-wiki\"><span class=\"newtab-shortcut-icon\">&#x1F4D6;</span><span class=\"newtab-shortcut-title\">Wikipedia</span></div><div class=\"newtab-shortcut\" id=\"shortcut-tor\"><span class=\"newtab-shortcut-icon\">&#x1F9C5;</span><span class=\"newtab-shortcut-title\">Tor Project</span></div><div class=\"newtab-shortcut\" id=\"shortcut-github\"><span class=\"newtab-shortcut-icon\">&#x1F47E;</span><span class=\"newtab-shortcut-title\">GitHub</span></div></div><div class=\"newtab-circuit-info\"><strong>&#x1F512; Secure DHT Onion Circuit:</strong> Traffic is encrypted and routed through multiple nodes of the Ernos decentralized network. No tracking, no censorship.</div></div>";
    set_prop(contentArea, "innerHTML", newTabHtml);
    form = document.getElementById("newtab-search-form");
    if (form) {
        form.addEventListener("submit", (event) => {
    inputVal = document.getElementById("newtab-search-input").value;
    navigateActiveTab(inputVal, false);
});
    }
    scDdg = document.getElementById("shortcut-ddg");
    if (scDdg) {
        scDdg.addEventListener("click", (event) => {
    navigateActiveTab("https://html.duckduckgo.com/html/", false);
});
    }
    scWiki = document.getElementById("shortcut-wiki");
    if (scWiki) {
        scWiki.addEventListener("click", (event) => {
    navigateActiveTab("https://www.wikipedia.org", false);
});
    }
    scTor = document.getElementById("shortcut-tor");
    if (scTor) {
        scTor.addEventListener("click", (event) => {
    navigateActiveTab("https://www.torproject.org", false);
});
    }
    scGithub = document.getElementById("shortcut-github");
    if (scGithub) {
        scGithub.addEventListener("click", (event) => {
    navigateActiveTab("https://github.com", false);
});
    }
    return 0;
}

function handleOnionViewResult(msg) {
    let urlParts, progressBar, tabId, tStart, tEnd, title, activeTab, htmlLower, contentArea, targetTab, loader;
    tabId = msg.tabId;
    targetTab = null;
    window.browserTabs.forEach((t) => {
    if ((t.id === tabId)) {
        targetTab = t;
    }
});
    if (!targetTab) {
        window.browserTabs.forEach((t) => {
    if ((t.id === window.activeTabId)) {
        targetTab = t;
    }
});
    }
    if (!targetTab) {
        return 0;
    }
    targetTab.loading = false;
    targetTab.html = msg.html;
    title = "Page Title";
    htmlLower = msg.html.toLowerCase();
    tStart = htmlLower.indexOf("<title>");
    if ((tStart >= 0)) {
        tEnd = htmlLower.indexOf("</title>", tStart);
        if ((tEnd >= 0)) {
            title = msg.html.substring((tStart + 7), tEnd).trim();
        } else {
            urlParts = msg.url.split("/");
            if ((urlParts.length > 2)) {
                title = Reflect.get(urlParts, 2);
            } else {
                title = msg.url;
            }
        }
    } else {
        urlParts = msg.url.split("/");
        if ((urlParts.length > 2)) {
            title = Reflect.get(urlParts, 2);
        } else {
            title = msg.url;
        }
    }
    targetTab.title = title;
    if ((targetTab.id === window.activeTabId)) {
        progressBar = document.getElementById("browser-progress-bar");
        if (progressBar) {
            set_prop(progressBar.style, "width", "100%");
            setTimeout((dummy) => {
    set_prop(progressBar.style, "width", "0%");
}, 500);
        }
        loader = document.getElementById("reader-modal-loader");
        contentArea = document.getElementById("reader-modal-content");
        set_prop(loader.style, "display", "none");
        set_prop(contentArea.style, "display", "block");
        set_prop(contentArea, "innerHTML", ((("<base href=\"" + String(targetTab.url)) + "\">") + msg.html));
        interceptViewportClicks();
    }
    renderBrowserTabs();
    activeTab = getActiveTab();
    if (activeTab) {
        updateNavButtons(activeTab);
        updateStarButton(activeTab);
    }
    return 0;
}

function updateGitDecRepos(reposStr) {
    let listContainer, parts;
    listContainer = document.getElementById("gitdec-repo-list");
    if (!listContainer) {
        return 0;
    }
    listContainer.innerHTML = "";
    if ((reposStr.length === 0)) {
        listContainer.innerHTML = "<div style='color: var(--text-muted); text-align: center; padding: 20px;'>No repositories loaded.</div>";
        return 0;
    }
    parts = reposStr.split(";");
    parts.forEach((part) => {
    if ((part.length > 0)) {
        kv = part.split(":");
        repoId = kv[0];
        vis = "public";
        if ((kv.length > 1)) {
            if ((kv[1].length > 0)) {
                vis = kv[1];
            }
        }
        if ((repoId.length > 0)) {
            row = document.createElement("div");
            row.className = "log-entry gitdec-repo-row";
            set_prop(row.style, "cursor", "pointer");
            set_prop(row.style, "margin-bottom", "5px");
            set_prop(row.style, "padding", "10px");
            set_prop(row.style, "border-radius", "6px");
            set_prop(row.style, "background", "rgba(255,255,255,0.03)");
            row.setAttribute("data-repo", repoId.toLowerCase());
            badgeTxt = "PUBLIC";
            if ((vis === "private")) {
                badgeTxt = "PRIVATE";
            }
            set_prop(row, "innerHTML", (((("<strong>📁 " + String(escapeHTML(repoId))) + "</strong><span class='did-pill small' style='float:right;font-size:0.65rem;opacity:0.75;'>") + String(badgeTxt)) + "</span>"));
            row.addEventListener("click", (event) => {
    selectGitDecRepo(repoId);
});
            listContainer.appendChild(row);
        }
    }
});
    return 0;
}

function selectGitDecRepo(repoId) {
    let viewerName, msg1, msgFileList, noSelected, msg3, viewerContent, detailsPanel, msg2, activeIdEl;
    window.gitdecActiveRepo = repoId;
    noSelected = document.getElementById("gitdec-no-repo-selected");
    detailsPanel = document.getElementById("gitdec-repo-details");
    set_prop(noSelected.style, "display", "none");
    set_prop(detailsPanel.style, "display", "block");
    activeIdEl = document.getElementById("gitdec-active-repo-id");
    activeIdEl.textContent = repoId;
    viewerName = document.getElementById("gitdec-active-file-name");
    viewerContent = document.getElementById("gitdec-file-viewer");
    if (viewerName) {
        viewerName.textContent = "Select a file to view";
    }
    if (viewerContent) {
        viewerContent.textContent = "";
    }
    msg1 = Object();
    msg1.type = "gitdec_get_repo_file";
    msg1.repo_id = repoId;
    msg1.filename = "gitdec.json";
    send_msg(window.ws, JSON.stringify(msg1));
    msg2 = Object();
    msg2.type = "gitdec_get_repo_file";
    msg2.repo_id = repoId;
    msg2.filename = "issues.json";
    send_msg(window.ws, JSON.stringify(msg2));
    msg3 = Object();
    msg3.type = "gitdec_get_repo_file";
    msg3.repo_id = repoId;
    msg3.filename = "pull_requests.json";
    send_msg(window.ws, JSON.stringify(msg3));
    msgFileList = Object();
    msgFileList.type = "gitdec_list_files";
    msgFileList.repo_id = repoId;
    send_msg(window.ws, JSON.stringify(msgFileList));
    return 0;
}

function handleGitDecFile(repoId, filename, content) {
    let sRepoName, b_keys, localRole, removeBtns, branchSelect, activeFileSpan, fileViewer, data, commitListEl, visVal, sRepoId, guideViewer, visToggle, visBadge, branches, manifest, titleEl, listEl, isOwner, issueListEl, keys, opt, auQuery, prListEl;
    if (((repoId === "ErnosDecent") && ((((((((((((filename === "docs/gitdec_user_guide.md") || (filename === "docs/system_guide_synthesis.md")) || (filename === "docs/ERNOS_REFERENCE.md")) || (filename === "README.md")) || (filename === "docs/settings_guide.md")) || (filename === "docs/identity_registry_guide.md")) || (filename === "docs/network_dht_guide.md")) || (filename === "docs/resource_pooling_guide.md")) || (filename === "docs/turing_hebbian_guide.md")) || (filename === "docs/messaging_social_guide.md")) || (filename === "docs/storage_crdt_guide.md")) || (filename === "docs/ledger_dex_guide.md")))) {
        guideViewer = document.getElementById("guide-text-content");
        if (guideViewer) {
            guideViewer.textContent = content;
        }
        return 0;
    }
    if ((repoId !== window.gitdecActiveRepo)) {
        return 0;
    }
    if ((filename === "gitdec.json")) {
        if ((content.length === 0)) {
            return 0;
        }
        manifest = JSON.parse(content);
        titleEl = document.getElementById("gitdec-active-repo-name");
        titleEl.textContent = (manifest.name || repoId);
        visVal = (manifest.visibility || "public");
        visBadge = document.getElementById("gitdec-visibility-badge");
        if (visBadge) {
            visBadge.textContent = visVal;
        }
        visToggle = document.getElementById("gitdec-btn-toggle-visibility");
        if (visToggle) {
            if ((visVal === "private")) {
                visToggle.textContent = "Make Public";
            } else {
                visToggle.textContent = "Make Private";
            }
        }
        branchSelect = document.getElementById("gitdec-active-branch");
        branchSelect.innerHTML = "";
        if (manifest.ref_heads) {
            branches = Object.keys(manifest.ref_heads);
            branches.forEach((b) => {
    opt = document.createElement("option");
    opt.value = b;
    opt.textContent = b;
    branchSelect.appendChild(opt);
});
            if ((branches.indexOf("main") < 0)) {
                opt = document.createElement("option");
                opt.value = "main";
                opt.textContent = "main";
                branchSelect.appendChild(opt);
            }
        } else {
            opt = document.createElement("option");
            opt.value = "main";
            opt.textContent = "main";
            branchSelect.appendChild(opt);
        }
        commitListEl = document.getElementById("gitdec-commit-list");
        commitListEl.innerHTML = "";
        if (manifest.ref_heads) {
            b_keys = Object.keys(manifest.ref_heads);
            b_keys.forEach((bName) => {
    c_hash = manifest.ref_heads[bName];
    row = document.createElement("div");
    row.className = "log-entry";
    set_prop(row, "innerHTML", (((("<span style='color: var(--neon-cyan);'>[" + String(escapeHTML(bName))) + "]</span> commit <code style='color: var(--neon-purple);'>") + String(escapeHTML(c_hash))) + "</code>"));
    commitListEl.appendChild(row);
});
        } else {
            commitListEl.innerHTML = "<div class='log-entry' style='color: var(--text-muted);'>No commits found. Pushes will appear here.</div>";
        }
        window.gitdecActiveManifest = manifest;
        sRepoName = document.getElementById("gitdec-settings-repo-name");
        sRepoId = document.getElementById("gitdec-settings-repo-id");
        if ((sRepoName && sRepoId)) {
            sRepoName.textContent = (manifest.name || repoId);
            sRepoId.textContent = repoId;
        }
        auQuery = Object();
        auQuery.type = "gitdec_get_auto_update";
        auQuery.repo_id = repoId;
        send_msg(window.ws, JSON.stringify(auQuery));
        listEl = document.getElementById("gitdec-settings-collabs-list");
        if (listEl) {
            listEl.innerHTML = "";
            isOwner = 0;
            if ((window.localIdentityDid && manifest.authorized_collaborators)) {
                localRole = manifest.authorized_collaborators[window.localIdentityDid];
                if ((localRole === "owner")) {
                    isOwner = 1;
                }
            }
            if (manifest.authorized_collaborators) {
                keys = Object.keys(manifest.authorized_collaborators);
                if ((keys.length > 0)) {
                    keys.forEach((k) => {
    r = manifest.authorized_collaborators[k];
    row = document.createElement("div");
    row.className = "log-entry";
    set_prop(row.style, "display", "flex");
    set_prop(row.style, "justify-content", "space-between");
    set_prop(row.style, "align-items", "center");
    set_prop(row.style, "margin-bottom", "8px");
    innerHTMLVal = (((("<div><span class='badge badge-cyan' style='margin-right: 8px;'>" + String(escapeHTML(r))) + "</span><code style='font-size:0.8rem; word-break: break-all;'>") + String(escapeHTML(k))) + "</code></div>");
    if (((isOwner === 1) && ((r === "owner") === 0))) {
        innerHTMLVal = (innerHTMLVal + (("<button class='btn-danger btn-sm gitdec-btn-remove-collab' data-collab-did='" + String(escapeHTML(k))) + "' style='background:#ef4444; border:none; color:white; padding:4px 8px; border-radius:4px; font-size:0.75rem; cursor:pointer;'>Remove</button>"));
    }
    set_prop(row, "innerHTML", innerHTMLVal);
    listEl.appendChild(row);
});
                    removeBtns = listEl.querySelectorAll(".gitdec-btn-remove-collab");
                    removeBtns.forEach((btn) => {
    btn.addEventListener("click", (e) => {
    targetDid = btn.getAttribute("data-collab-did");
    if (confirm((("Are you sure you want to remove collaborator " + String(targetDid)) + "?"))) {
        removeMsg = Object();
        removeMsg.type = "gitdec_remove_collab";
        removeMsg.repo_id = repoId;
        removeMsg.collab_did = targetDid;
        send_msg(window.ws, JSON.stringify(removeMsg));
    }
});
});
                } else {
                    listEl.innerHTML = "<div class='log-entry' style='color: var(--text-muted);'>No collaborators loaded.</div>";
                }
            } else {
                listEl.innerHTML = "<div class='log-entry' style='color: var(--text-muted);'>No collaborators loaded.</div>";
            }
        }
    } else if ((filename === "issues.json")) {
        issueListEl = document.getElementById("gitdec-issue-list");
        issueListEl.innerHTML = "";
        if ((content.length === 0)) {
            issueListEl.innerHTML = "<div class='log-entry' style='color: var(--text-muted);'>No issues found.</div>";
            return 0;
        }
        data = JSON.parse(content);
        if ((!data.issues || (data.issues.length === 0))) {
            issueListEl.innerHTML = "<div class='log-entry' style='color: var(--text-muted);'>No issues found.</div>";
            return 0;
        }
        data.issues.forEach((issue) => {
    row = document.createElement("div");
    row.className = "log-entry";
    set_prop(row.style, "cursor", "pointer");
    badgeClass = "badge-green";
    if ((issue.status !== "open")) {
        badgeClass = "badge-muted";
    }
    set_prop(row, "innerHTML", (((((((("<strong>#" + String(escapeHTML(issue.id))) + "</strong> ") + String(escapeHTML(issue.title))) + " <span class='badge ") + String(badgeClass)) + "' style='float:right;'>") + String(escapeHTML(issue.status))) + "</span>"));
    row.addEventListener("click", (event) => {
    showGitDecIssueDetail(issue);
});
    issueListEl.appendChild(row);
});
        if (window.gitdecActiveIssue) {
            data.issues.forEach((freshIssue) => {
    if ((freshIssue.id === window.gitdecActiveIssue.id)) {
        showGitDecIssueDetail(freshIssue);
    }
});
        }
    } else if ((filename === "pull_requests.json")) {
        prListEl = document.getElementById("gitdec-pr-list");
        prListEl.innerHTML = "";
        if ((content.length === 0)) {
            prListEl.innerHTML = "<div class='log-entry' style='color: var(--text-muted);'>No PRs found.</div>";
            return 0;
        }
        data = JSON.parse(content);
        if ((!data.pull_requests || (data.pull_requests.length === 0))) {
            prListEl.innerHTML = "<div class='log-entry' style='color: var(--text-muted);'>No PRs found.</div>";
            return 0;
        }
        data.pull_requests.forEach((pr) => {
    row = document.createElement("div");
    row.className = "log-entry";
    set_prop(row.style, "cursor", "pointer");
    badgeClass = "badge-cyan";
    if ((pr.status === "approved")) {
        badgeClass = "badge-green";
    } else if ((pr.status !== "open")) {
        badgeClass = "badge-muted";
    }
    set_prop(row, "innerHTML", (((((((("<strong>#" + String(escapeHTML(pr.id))) + "</strong> ") + String(escapeHTML(pr.title))) + " <span class='badge ") + String(badgeClass)) + "' style='float:right;'>") + String(escapeHTML(pr.status))) + "</span>"));
    row.addEventListener("click", (event) => {
    showGitDecPrDetail(pr);
});
    prListEl.appendChild(row);
});
    } else {
        activeFileSpan = document.getElementById("gitdec-active-file-name");
        fileViewer = document.getElementById("gitdec-file-viewer");
        if ((activeFileSpan && fileViewer)) {
            activeFileSpan.textContent = filename;
            fileViewer.textContent = content;
        }
    }
    return 0;
}

function renderGitDecFiles(repoId, filesStr) {
    let files, fileListEl, count;
    if ((repoId !== window.gitdecActiveRepo)) {
        return 0;
    }
    fileListEl = document.getElementById("gitdec-file-list");
    if (!fileListEl) {
        return 0;
    }
    fileListEl.innerHTML = "";
    if ((filesStr.length === 0)) {
        fileListEl.innerHTML = "<div class='log-entry' style='color: var(--text-muted);'>No files found.</div>";
        return 0;
    }
    files = filesStr.split(";");
    count = 0;
    files.forEach((f) => {
    if (((((((f !== "gitdec.json") && (f !== "issues.json")) && (f !== "pull_requests.json")) && (f !== "objects")) && (f !== ".git")) && (f !== ".DS_Store"))) {
        row = document.createElement("div");
        row.className = "log-entry";
        set_prop(row.style, "cursor", "pointer");
        set_prop(row.style, "padding", "6px 8px");
        set_prop(row.style, "border-radius", "4px");
        set_prop(row.style, "margin-bottom", "4px");
        row.textContent = f;
        row.addEventListener("mouseover", (e) => {
    set_prop(row.style, "background", "rgba(255,255,255,0.05)");
});
        row.addEventListener("mouseout", (e) => {
    set_prop(row.style, "background", "transparent");
});
        row.addEventListener("click", (e) => {
    items = fileListEl.querySelectorAll(".log-entry");
    items.forEach((item) => {
    set_prop(item.style, "color", "var(--text-color)");
    set_prop(item.style, "font-weight", "normal");
});
    set_prop(row.style, "color", "var(--neon-cyan)");
    set_prop(row.style, "font-weight", "bold");
    viewerHeader = document.getElementById("gitdec-active-file-name");
    viewerHeader.textContent = ("Loading " + f);
    msg = Object();
    msg.type = "gitdec_get_repo_file";
    msg.repo_id = repoId;
    msg.filename = f;
    send_msg(window.ws, JSON.stringify(msg));
});
        fileListEl.appendChild(row);
        count = (count + 1);
    }
});
    if ((count === 0)) {
        fileListEl.innerHTML = "<div class='log-entry' style='color: var(--text-muted);'>No source files.</div>";
    }
    return 0;
}

function showGitDecIssueDetail(issue) {
    let titleEl, bodyRow, commentsContainer, detailCard;
    window.gitdecActiveIssue = issue;
    detailCard = document.getElementById("gitdec-issue-detail-card");
    set_prop(detailCard.style, "display", "block");
    titleEl = document.getElementById("gitdec-active-issue-title");
    titleEl.textContent = ((("#" + String(issue.id)) + ": ") + String(issue.title));
    commentsContainer = document.getElementById("gitdec-issue-comments");
    commentsContainer.innerHTML = "";
    bodyRow = document.createElement("div");
    set_prop(bodyRow.style, "margin-bottom", "15px");
    set_prop(bodyRow.style, "border-bottom", "1px solid rgba(255,255,255,0.05)");
    set_prop(bodyRow.style, "padding-bottom", "10px");
    set_prop(bodyRow, "innerHTML", (((("<div style='font-weight:bold; color:var(--neon-cyan);'>" + String(escapeHTML(issue.author))) + "</div><div style='margin-top:5px;'>") + String(escapeHTML(issue.body))) + "</div>"));
    commentsContainer.appendChild(bodyRow);
    if (issue.comments) {
        issue.comments.forEach((comment) => {
    row = document.createElement("div");
    set_prop(row.style, "margin-bottom", "10px");
    set_prop(row, "innerHTML", (((("<div style='font-size:0.8rem; color:var(--text-muted);'>" + String(escapeHTML(comment.author))) + " commented:</div><div style='margin-top:2px;'>") + String(escapeHTML(comment.text))) + "</div>"));
    commentsContainer.appendChild(row);
});
    }
    return 0;
}

function showGitDecPrDetail(pr) {
    let reviewsContainer, descRow, detailCard, titleEl, branchEl;
    window.gitdecActivePr = pr;
    detailCard = document.getElementById("gitdec-pr-detail-card");
    set_prop(detailCard.style, "display", "block");
    titleEl = document.getElementById("gitdec-active-pr-title");
    titleEl.textContent = ((("#" + String(pr.id)) + ": ") + String(pr.title));
    branchEl = document.getElementById("gitdec-active-pr-branches");
    branchEl.textContent = ((("merge: " + String(pr.source_branch)) + " -> ") + String(pr.target_branch));
    reviewsContainer = document.getElementById("gitdec-pr-reviews");
    reviewsContainer.innerHTML = "";
    descRow = document.createElement("div");
    set_prop(descRow.style, "margin-bottom", "15px");
    set_prop(descRow.style, "border-bottom", "1px solid rgba(255,255,255,0.05)");
    set_prop(descRow.style, "padding-bottom", "10px");
    set_prop(descRow, "innerHTML", (((("<div style='font-weight:bold; color:var(--neon-cyan);'>" + String(escapeHTML(pr.author))) + "</div><div style='margin-top:5px;'>") + String(escapeHTML(pr.description))) + "</div>"));
    reviewsContainer.appendChild(descRow);
    if (pr.reviews) {
        pr.reviews.forEach((review) => {
    row = document.createElement("div");
    set_prop(row.style, "margin-bottom", "10px");
    badgeColor = "var(--neon-cyan)";
    if ((review.decision === "approve")) {
        badgeColor = "var(--neon-green)";
    } else {
        badgeColor = "var(--neon-red)";
    }
    set_prop(row, "innerHTML", (((((((("<div style='font-size:0.8rem; color:var(--text-muted);'>" + String(escapeHTML(review.reviewer))) + " reviewed (<span style='color:") + String(badgeColor)) + ";font-weight:bold;'>") + String(escapeHTML(review.decision))) + "</span>):</div><div style='margin-top:2px;'>") + String(escapeHTML(review.comment))) + "</div>"));
    reviewsContainer.appendChild(row);
});
    }
    return 0;
}

function initGuide() {
    let msg, btns, navList, file, activeBtn;
    navList = document.getElementById("guide-nav-list");
    if (!navList) {
        return 0;
    }
    btns = navList.querySelectorAll("button");
    btns.forEach((btn) => {
    btn.addEventListener("click", (e) => {
    btns.forEach((b) => {
    b.classList.remove("active");
});
    btn.classList.add("active");
    file = btn.getAttribute("data-guide-file");
    viewer = document.getElementById("guide-text-content");
    if (viewer) {
        viewer.textContent = ("Loading " + file);
    }
    msg = Object();
    msg.type = "gitdec_get_repo_file";
    msg.repo_id = "ErnosDecent";
    msg.filename = file;
    send_msg(window.ws, JSON.stringify(msg));
});
});
    activeBtn = navList.querySelector("button.active");
    if (activeBtn) {
        file = activeBtn.getAttribute("data-guide-file");
        msg = Object();
        msg.type = "gitdec_get_repo_file";
        msg.repo_id = "ErnosDecent";
        msg.filename = file;
        send_msg(window.ws, JSON.stringify(msg));
    }
    return 0;
}

function initGitDec() {
    let filesPanel, issuesPanel, formCreateIssue, formCommentIssue, formSettingsAddCollab, prsPanel, btnToggleVis, formCloneRepo, formReviewPr, filesBtn, btnCloseNewIssue, btnCloseNewPr, btnCloseCloneRepo, btnNewPr, btnImportRepo, modalCloneRepo, repoSearch, modalNewPr, btnCloneRepo, btnDeleteRepo, commitsPanel, btnNewRepo, formCreateRepo, commitsBtn, btnMergeMain, settingsBtn, settingsPanel, btnCloseImportRepo, autoUpdateToggle, modalImportRepo, btnCloseIssue, formCreatePr, btnCloseNewRepo, formImportRepo, issuesBtn, prsBtn, btnNewIssue, modalNewIssue, modalNewRepo;
    commitsBtn = document.getElementById("gitdec-tab-commits");
    filesBtn = document.getElementById("gitdec-tab-files");
    issuesBtn = document.getElementById("gitdec-tab-issues");
    prsBtn = document.getElementById("gitdec-tab-prs");
    settingsBtn = document.getElementById("gitdec-tab-settings");
    commitsPanel = document.getElementById("gitdec-panel-commits");
    filesPanel = document.getElementById("gitdec-panel-files");
    issuesPanel = document.getElementById("gitdec-panel-issues");
    prsPanel = document.getElementById("gitdec-panel-prs");
    settingsPanel = document.getElementById("gitdec-panel-settings");
    if (((((commitsBtn && filesBtn) && issuesBtn) && prsBtn) && settingsBtn)) {
        commitsBtn.addEventListener("click", (event) => {
    commitsBtn.classList.add("active");
    filesBtn.classList.remove("active");
    issuesBtn.classList.remove("active");
    prsBtn.classList.remove("active");
    settingsBtn.classList.remove("active");
    set_prop(commitsPanel.style, "display", "block");
    set_prop(filesPanel.style, "display", "none");
    set_prop(issuesPanel.style, "display", "none");
    set_prop(prsPanel.style, "display", "none");
    set_prop(settingsPanel.style, "display", "none");
});
        filesBtn.addEventListener("click", (event) => {
    commitsBtn.classList.remove("active");
    filesBtn.classList.add("active");
    issuesBtn.classList.remove("active");
    prsBtn.classList.remove("active");
    settingsBtn.classList.remove("active");
    set_prop(commitsPanel.style, "display", "none");
    set_prop(filesPanel.style, "display", "block");
    set_prop(issuesPanel.style, "display", "none");
    set_prop(prsPanel.style, "display", "none");
    set_prop(settingsPanel.style, "display", "none");
});
        issuesBtn.addEventListener("click", (event) => {
    commitsBtn.classList.remove("active");
    filesBtn.classList.remove("active");
    issuesBtn.classList.add("active");
    prsBtn.classList.remove("active");
    settingsBtn.classList.remove("active");
    set_prop(commitsPanel.style, "display", "none");
    set_prop(filesPanel.style, "display", "none");
    set_prop(issuesPanel.style, "display", "block");
    set_prop(prsPanel.style, "display", "none");
    set_prop(settingsPanel.style, "display", "none");
});
        prsBtn.addEventListener("click", (event) => {
    commitsBtn.classList.remove("active");
    filesBtn.classList.remove("active");
    issuesBtn.classList.remove("active");
    prsBtn.classList.add("active");
    settingsBtn.classList.remove("active");
    set_prop(commitsPanel.style, "display", "none");
    set_prop(filesPanel.style, "display", "none");
    set_prop(issuesPanel.style, "display", "none");
    set_prop(prsPanel.style, "display", "block");
    set_prop(settingsPanel.style, "display", "none");
});
        settingsBtn.addEventListener("click", (event) => {
    commitsBtn.classList.remove("active");
    filesBtn.classList.remove("active");
    issuesBtn.classList.remove("active");
    prsBtn.classList.remove("active");
    settingsBtn.classList.add("active");
    set_prop(commitsPanel.style, "display", "none");
    set_prop(filesPanel.style, "display", "none");
    set_prop(issuesPanel.style, "display", "none");
    set_prop(prsPanel.style, "display", "none");
    set_prop(settingsPanel.style, "display", "block");
});
    }
    btnNewRepo = document.getElementById("gitdec-btn-new-repo");
    modalNewRepo = document.getElementById("gitdec-modal-create-repo");
    btnCloseNewRepo = document.getElementById("gitdec-btn-close-create-repo");
    if (((btnNewRepo && modalNewRepo) && btnCloseNewRepo)) {
        btnNewRepo.addEventListener("click", (event) => {
    modalNewRepo.classList.add("active");
});
        btnCloseNewRepo.addEventListener("click", (event) => {
    modalNewRepo.classList.remove("active");
});
    }
    btnCloneRepo = document.getElementById("gitdec-btn-clone-repo");
    modalCloneRepo = document.getElementById("gitdec-modal-clone-repo");
    btnCloseCloneRepo = document.getElementById("gitdec-btn-close-clone-repo");
    if (((btnCloneRepo && modalCloneRepo) && btnCloseCloneRepo)) {
        btnCloneRepo.addEventListener("click", (event) => {
    modalCloneRepo.classList.add("active");
});
        btnCloseCloneRepo.addEventListener("click", (event) => {
    modalCloneRepo.classList.remove("active");
});
    }
    btnImportRepo = document.getElementById("gitdec-btn-import-repo");
    modalImportRepo = document.getElementById("gitdec-modal-import-repo");
    btnCloseImportRepo = document.getElementById("gitdec-btn-close-import-repo");
    if (((btnImportRepo && modalImportRepo) && btnCloseImportRepo)) {
        btnImportRepo.addEventListener("click", (event) => {
    modalImportRepo.classList.add("active");
});
        btnCloseImportRepo.addEventListener("click", (event) => {
    modalImportRepo.classList.remove("active");
});
    }
    btnNewIssue = document.getElementById("gitdec-btn-new-issue");
    modalNewIssue = document.getElementById("gitdec-modal-create-issue");
    btnCloseNewIssue = document.getElementById("gitdec-btn-close-create-issue");
    if (((btnNewIssue && modalNewIssue) && btnCloseNewIssue)) {
        btnNewIssue.addEventListener("click", (event) => {
    modalNewIssue.classList.add("active");
});
        btnCloseNewIssue.addEventListener("click", (event) => {
    modalNewIssue.classList.remove("active");
});
    }
    btnNewPr = document.getElementById("gitdec-btn-new-pr");
    modalNewPr = document.getElementById("gitdec-modal-create-pr");
    btnCloseNewPr = document.getElementById("gitdec-btn-close-create-pr");
    if (((btnNewPr && modalNewPr) && btnCloseNewPr)) {
        btnNewPr.addEventListener("click", (event) => {
    modalNewPr.classList.add("active");
});
        btnCloseNewPr.addEventListener("click", (event) => {
    modalNewPr.classList.remove("active");
});
    }
    btnDeleteRepo = document.getElementById("gitdec-btn-delete-repo");
    if (btnDeleteRepo) {
        btnDeleteRepo.addEventListener("click", (event) => {
    if (confirm("Are you sure you want to permanently delete this repository from this node and request other nodes to clean it up?")) {
        msg = Object();
        msg.type = "gitdec_delete_repo";
        msg.repo_id = window.gitdecActiveRepo;
        send_msg(window.ws, JSON.stringify(msg));
    }
});
    }
    autoUpdateToggle = document.getElementById("gitdec-settings-autoupdate-toggle");
    if (autoUpdateToggle) {
        autoUpdateToggle.addEventListener("change", (event) => {
    msg = Object();
    msg.type = "gitdec_set_auto_update";
    msg.repo_id = window.gitdecActiveRepo;
    if (autoUpdateToggle.checked) {
        msg.enabled = 1;
    } else {
        msg.enabled = 0;
    }
    send_msg(window.ws, JSON.stringify(msg));
});
    }
    btnMergeMain = document.getElementById("gitdec-btn-merge-main");
    if (btnMergeMain) {
        btnMergeMain.addEventListener("click", (event) => {
    branchSel = document.getElementById("gitdec-active-branch");
    srcBranch = branchSel.value;
    if ((srcBranch === "main")) {
        alert("Select a non-main branch to merge into main.");
    } else if (confirm(("Merge branch '" + (srcBranch + "' into main and broadcast to the network?")))) {
        msg = Object();
        msg.type = "gitdec_merge";
        msg.repo_id = window.gitdecActiveRepo;
        msg.source_branch = srcBranch;
        send_msg(window.ws, JSON.stringify(msg));
    }
});
    }
    btnToggleVis = document.getElementById("gitdec-btn-toggle-visibility");
    if (btnToggleVis) {
        btnToggleVis.addEventListener("click", (event) => {
    curBadge = document.getElementById("gitdec-visibility-badge");
    newVis = "private";
    if ((curBadge.textContent === "private")) {
        newVis = "public";
    }
    msg = Object();
    msg.type = "gitdec_set_visibility";
    msg.repo_id = window.gitdecActiveRepo;
    msg.visibility = newVis;
    send_msg(window.ws, JSON.stringify(msg));
});
    }
    repoSearch = document.getElementById("gitdec-repo-search");
    if (repoSearch) {
        repoSearch.addEventListener("input", (event) => {
    q = repoSearch.value.toLowerCase();
    rows = document.querySelectorAll(".gitdec-repo-row");
    rows.forEach((row) => {
    rid = (row.getAttribute("data-repo") || "");
    if (rid.includes(q)) {
        set_prop(row.style, "display", "block");
    } else {
        set_prop(row.style, "display", "none");
    }
});
});
    }
    formCreateRepo = document.getElementById("gitdec-form-create-repo");
    if (formCreateRepo) {
        formCreateRepo.addEventListener("submit", (event) => {
    event.preventDefault();
    repoIdInput = document.getElementById("gitdec-input-repo-id");
    repoNameInput = document.getElementById("gitdec-input-repo-name");
    repoId = repoIdInput.value;
    name = repoNameInput.value;
    msg = Object();
    msg.type = "gitdec_create_repo";
    msg.repo_id = repoId;
    msg.name = name;
    send_msg(window.ws, JSON.stringify(msg));
    modalNewRepo.classList.remove("active");
    repoIdInput.value = "";
    repoNameInput.value = "";
    setTimeout((dummy) => {
    refresh = Object();
    refresh.type = "gitdec_get_repos";
    send_msg(window.ws, JSON.stringify(refresh));
}, 500);
});
    }
    formCloneRepo = document.getElementById("gitdec-form-clone-repo");
    if (formCloneRepo) {
        formCloneRepo.addEventListener("submit", (event) => {
    event.preventDefault();
    repoIdInput = document.getElementById("gitdec-input-clone-repo-id");
    repoId = repoIdInput.value;
    msg = Object();
    msg.type = "gitdec_clone_repo";
    msg.repo_id = repoId;
    send_msg(window.ws, JSON.stringify(msg));
    modalCloneRepo.classList.remove("active");
    repoIdInput.value = "";
    setTimeout((dummy) => {
    refresh = Object();
    refresh.type = "gitdec_get_repos";
    send_msg(window.ws, JSON.stringify(refresh));
}, 1500);
});
    }
    formImportRepo = document.getElementById("gitdec-form-import-repo");
    if (formImportRepo) {
        formImportRepo.addEventListener("submit", (event) => {
    event.preventDefault();
    importNameInput = document.getElementById("gitdec-input-import-name");
    importPathInput = document.getElementById("gitdec-input-import-path");
    importName = importNameInput.value;
    importPath = importPathInput.value;
    msg = Object();
    msg.type = "gitdec_import_repo";
    msg.name = importName;
    msg.path = importPath;
    send_msg(window.ws, JSON.stringify(msg));
    modalImportRepo.classList.remove("active");
    importNameInput.value = "";
    importPathInput.value = "";
    setTimeout((dummy) => {
    refresh = Object();
    refresh.type = "gitdec_get_repos";
    send_msg(window.ws, JSON.stringify(refresh));
}, 2500);
});
    }
    formSettingsAddCollab = document.getElementById("gitdec-settings-form-add-collab");
    if (formSettingsAddCollab) {
        formSettingsAddCollab.addEventListener("submit", (event) => {
    event.preventDefault();
    collabDidInput = document.getElementById("gitdec-settings-input-collab-did");
    collabRoleInput = document.getElementById("gitdec-settings-select-collab-role");
    collabDid = collabDidInput.value;
    role = collabRoleInput.value;
    msg = Object();
    msg.type = "gitdec_add_collab";
    msg.repo_id = window.gitdecActiveRepo;
    msg.collab_did = collabDid;
    msg.role = role;
    send_msg(window.ws, JSON.stringify(msg));
    collabDidInput.value = "";
});
    }
    formCreateIssue = document.getElementById("gitdec-form-create-issue");
    if (formCreateIssue) {
        formCreateIssue.addEventListener("submit", (event) => {
    event.preventDefault();
    titleInput = document.getElementById("gitdec-input-issue-title");
    bodyInput = document.getElementById("gitdec-input-issue-body");
    msg = Object();
    msg.type = "gitdec_create_issue";
    msg.repo_id = window.gitdecActiveRepo;
    msg.title = titleInput.value;
    msg.body = bodyInput.value;
    send_msg(window.ws, JSON.stringify(msg));
    modalNewIssue.classList.remove("active");
    titleInput.value = "";
    bodyInput.value = "";
    setTimeout((dummy) => {
    refresh = Object();
    refresh.type = "gitdec_get_repo_file";
    refresh.repo_id = window.gitdecActiveRepo;
    refresh.filename = "issues.json";
    send_msg(window.ws, JSON.stringify(refresh));
}, 500);
});
    }
    formCommentIssue = document.getElementById("gitdec-comment-form");
    if (formCommentIssue) {
        formCommentIssue.addEventListener("submit", (event) => {
    event.preventDefault();
    commentInput = document.getElementById("gitdec-comment-input");
    msg = Object();
    msg.type = "gitdec_comment_issue";
    msg.repo_id = window.gitdecActiveRepo;
    msg.issue_id = window.gitdecActiveIssue.id;
    msg.comment = commentInput.value;
    send_msg(window.ws, JSON.stringify(msg));
    commentInput.value = "";
    setTimeout((dummy) => {
    refresh = Object();
    refresh.type = "gitdec_get_repo_file";
    refresh.repo_id = window.gitdecActiveRepo;
    refresh.filename = "issues.json";
    send_msg(window.ws, JSON.stringify(refresh));
}, 500);
});
    }
    btnCloseIssue = document.getElementById("gitdec-btn-close-issue");
    if (btnCloseIssue) {
        btnCloseIssue.addEventListener("click", (event) => {
    if (window.gitdecActiveIssue) {
        closeMsg = Object();
        closeMsg.type = "gitdec_close_issue";
        closeMsg.repo_id = window.gitdecActiveRepo;
        closeMsg.issue_id = window.gitdecActiveIssue.id;
        send_msg(window.ws, JSON.stringify(closeMsg));
        setTimeout((dummy) => {
    closeRefresh = Object();
    closeRefresh.type = "gitdec_get_repo_file";
    closeRefresh.repo_id = window.gitdecActiveRepo;
    closeRefresh.filename = "issues.json";
    send_msg(window.ws, JSON.stringify(closeRefresh));
}, 500);
    }
});
    }
    formCreatePr = document.getElementById("gitdec-form-create-pr");
    if (formCreatePr) {
        formCreatePr.addEventListener("submit", (event) => {
    event.preventDefault();
    titleInput = document.getElementById("gitdec-input-pr-title");
    sourceInput = document.getElementById("gitdec-input-pr-source");
    targetInput = document.getElementById("gitdec-input-pr-target");
    descInput = document.getElementById("gitdec-input-pr-desc");
    msg = Object();
    msg.type = "gitdec_create_pr";
    msg.repo_id = window.gitdecActiveRepo;
    msg.title = titleInput.value;
    msg.source = sourceInput.value;
    msg.target = targetInput.value;
    msg.description = descInput.value;
    send_msg(window.ws, JSON.stringify(msg));
    modalNewPr.classList.remove("active");
    titleInput.value = "";
    sourceInput.value = "";
    descInput.value = "";
    setTimeout((dummy) => {
    refresh = Object();
    refresh.type = "gitdec_get_repo_file";
    refresh.repo_id = window.gitdecActiveRepo;
    refresh.filename = "pull_requests.json";
    send_msg(window.ws, JSON.stringify(refresh));
}, 500);
});
    }
    formReviewPr = document.getElementById("gitdec-review-form");
    if (formReviewPr) {
        formReviewPr.addEventListener("submit", (event) => {
    event.preventDefault();
    commentInput = document.getElementById("gitdec-review-comment");
    decisionSelect = document.getElementById("gitdec-review-decision");
    msg = Object();
    msg.type = "gitdec_review_pr";
    msg.repo_id = window.gitdecActiveRepo;
    msg.pr_id = window.gitdecActivePr.id;
    msg.decision = decisionSelect.value;
    msg.comment = commentInput.value;
    send_msg(window.ws, JSON.stringify(msg));
    commentInput.value = "";
    setTimeout((dummy) => {
    refresh = Object();
    refresh.type = "gitdec_get_repo_file";
    refresh.repo_id = window.gitdecActiveRepo;
    refresh.filename = "pull_requests.json";
    send_msg(window.ws, JSON.stringify(refresh));
}, 500);
});
    }
    return 0;
}

function main() {
    let btnTriggerAutonomy, navItems, toggleTelegram, wikiBookmark, channelBtns, aiForm, btnAddPlugin, readerModalHtml, guideSections, btnSaveWhatsapp, tabPanels, btnCloseBrowser, btnNewSession, transferForm, menuBookmarkOption, nameForm, dhtForm, toggleWhatsapp, btnForward, btnBack, turingForm, pageTitle, savedTab, btnSaveSystemConfig, btnHome, btnSaveTelegram, aiModelSelect, onionCard, dhtCardWide, menuNewIncognito, menuNewTab, btnSwapTokens, btnStar, btnReload, btnAddTab, subTabs, networkGrid, guideBtns, btnSaveDiscord, addressInput, nameInput, toggleDiscord, btnRefreshHosts, menuReloadOption, ddgBookmark, btnDecayMemory, clickFn, readerModal, btnSavePrompts, onionSearchHtml, btnMenu, onionForm, torBookmark, targetBtn, menuExitOption, chatForm, savedLastName;
    window.ws = null;
    window.isConnected = false;
    window.uptimeSeconds = 0;
    window.activeChannel = "general-mesh";
    window.activeSessionId = "default";
    window.selectedAiModel = "";
    window.currentAiResponseBubble = null;
    window.graphNodes = Object();
    window.graphLinks = [];
    window.canvasElement = null;
    window.canvasCtx = null;
    window.animationFrameId = null;
    window.platforms = null;
    window.plugins = [];
    window.chatContainer = document.getElementById("chat-messages-container");
    window.aiContainer = document.getElementById("ai-messages-container");
    window.aiLoader = document.getElementById("ai-loader");
    window.aiInput = document.getElementById("ai-input-text");
    window.aiSystemPrompt = document.getElementById("ai-system-prompt");
    window.recipientDidInput = document.getElementById("recipient-did");
    window.transferAmountInput = document.getElementById("transfer-amount");
    window.swapFromAmount = document.getElementById("swap-from-amount");
    window.swapToAmount = document.getElementById("swap-to-amount");
    window.chatInput = document.getElementById("chat-input-text");
    dhtCardWide = document.querySelector("#tab-network .card-wide");
    if (dhtCardWide) {
        dhtCardWide.classList.remove("card-wide");
        dhtCardWide.classList.add("card");
        onionCard = document.createElement("div");
        onionCard.className = "card";
        onionCard.id = "onion-search-card";
        onionSearchHtml = "<h3>Private Onion Search Browser</h3><form id=\"onion-search-form\" class=\"standard-form inline-form\" onsubmit=\"return false;\"><div class=\"form-row\"><div class=\"form-group\" style=\"flex: 0 0 120px;\"><label for=\"onion-engine\">Engine</label><select id=\"onion-engine\"><option value=\"DuckDuckGo\">DuckDuckGo</option><option value=\"Google\">Google</option><option value=\"Bing\">Bing</option></select></div><div class=\"form-group\" style=\"flex: 1;\"><label for=\"onion-query-input\">Query</label><input type=\"text\" id=\"onion-query-input\" placeholder=\"Search privately...\" required></div><button type=\"submit\" class=\"btn-primary\" id=\"btn-onion-search\">Search Privately</button></div></form><div id=\"onion-circuit-container\" style=\"display: none; margin: 20px 0;\"><div class=\"circuit-title\">Secure Onion Route:</div><svg id=\"onion-circuit-svg\" width=\"100%\" height=\"80\" viewBox=\"0 0 400 80\"><line x1=\"50\" y1=\"40\" x2=\"150\" y2=\"40\" class=\"circuit-line\" /><line x1=\"150\" y1=\"40\" x2=\"250\" y2=\"40\" class=\"circuit-line\" /><line x1=\"250\" y1=\"40\" x2=\"350\" y2=\"40\" class=\"circuit-line\" /><circle cx=\"50\" cy=\"40\" r=\"4\" class=\"circuit-pulse\" id=\"pulse-1\" style=\"display:none;\"><animate attributeName=\"cx\" from=\"50\" to=\"150\" dur=\"0.3s\" fill=\"freeze\" begin=\"indefinite\" id=\"anim-1\" /></circle><circle cx=\"150\" cy=\"40\" r=\"4\" class=\"circuit-pulse\" id=\"pulse-2\" style=\"display:none;\"><animate attributeName=\"cx\" from=\"150\" to=\"250\" dur=\"0.3s\" fill=\"freeze\" begin=\"indefinite\" id=\"anim-2\" /></circle><circle cx=\"250\" cy=\"40\" r=\"4\" class=\"circuit-pulse\" id=\"pulse-3\" style=\"display:none;\"><animate attributeName=\"cx\" from=\"250\" to=\"350\" dur=\"0.4s\" fill=\"freeze\" begin=\"indefinite\" id=\"anim-3\" /></circle><circle cx=\"50\" cy=\"40\" r=\"12\" class=\"circuit-node client\" /><text x=\"50\" y=\"43\" class=\"circuit-node-label\" text-anchor=\"middle\">UA</text><circle cx=\"150\" cy=\"40\" r=\"10\" class=\"circuit-node guard\" /><text x=\"150\" y=\"43\" class=\"circuit-node-label\" text-anchor=\"middle\">G</text><circle cx=\"250\" cy=\"40\" r=\"10\" class=\"circuit-node middle\" /><text x=\"250\" y=\"43\" class=\"circuit-node-label\" text-anchor=\"middle\">M</text><circle cx=\"350\" cy=\"40\" r=\"12\" class=\"circuit-node exit\" /><text x=\"350\" y=\"43\" class=\"circuit-node-label\" text-anchor=\"middle\">E</text><text x=\"50\" y=\"68\" class=\"circuit-node-text\" text-anchor=\"middle\">Client</text><text x=\"150\" y=\"68\" class=\"circuit-node-text\" text-anchor=\"middle\">Guard</text><text x=\"250\" y=\"68\" class=\"circuit-node-text\" text-anchor=\"middle\">Middle</text><text x=\"350\" y=\"68\" class=\"circuit-node-text\" text-anchor=\"middle\">Exit</text></svg></div><div class=\"search-results-box\" id=\"onion-results-box\"><div style=\"color: var(--text-muted); text-align: center; padding: 20px 0;\">Anonymous search results will appear here...</div></div>";
        set_prop(onionCard, "innerHTML", onionSearchHtml);
        networkGrid = document.querySelector("#tab-network .grid-layout");
        if (networkGrid) {
            if (networkGrid.firstChild) {
                networkGrid.insertBefore(onionCard, networkGrid.firstChild);
            } else {
                networkGrid.appendChild(onionCard);
            }
        }
    }
    readerModal = document.createElement("div");
    readerModal.className = "modal-overlay";
    readerModal.id = "reader-view-modal";
    readerModalHtml = "<div class=\"browser-window\"><div class=\"browser-titlebar\"><div class=\"mac-dots\"><span class=\"dot close\"></span><span class=\"dot minimize\"></span><span class=\"dot maximize\"></span></div><div class=\"browser-tabbar\" id=\"browser-tabbar\"></div><button class=\"browser-add-tab-btn\" id=\"btn-browser-add-tab\">+</button><div class=\"browser-window-controls\"><button class=\"browser-close-btn\" id=\"btn-close-browser\">&times;</button></div></div><div class=\"browser-toolbar\"><div class=\"browser-nav-controls\"><button class=\"browser-nav-btn\" id=\"btn-browser-back\" title=\"Back\">&larr;</button><button class=\"browser-nav-btn\" id=\"btn-browser-forward\" title=\"Forward\">&rarr;</button><button class=\"browser-nav-btn\" id=\"btn-browser-reload\" title=\"Reload\">&#x21BB;</button><button class=\"browser-nav-btn\" id=\"btn-browser-home\" title=\"Home\">&#x2302;</button></div><div class=\"browser-address-container\"><span class=\"browser-security-icon\" id=\"browser-security-icon\">&#x1F9C5;</span><input type=\"text\" class=\"browser-address-input\" id=\"browser-address-input\" placeholder=\"Search privately or enter URL...\"><button class=\"browser-bookmark-star\" id=\"btn-browser-star\" title=\"Bookmark this page\">&#x2606;</button></div><div class=\"browser-extensions\"><button class=\"browser-ext-btn shield-active\" id=\"btn-browser-shield\" title=\"Ernos Shield: Active (Blocking Trackers)\">&#x1F6E1;</button><button class=\"browser-ext-btn\" id=\"btn-browser-menu\" title=\"Customize and control Ernos Browser\">&#x22EE;</button><div class=\"browser-menu-dropdown\" id=\"browser-menu-dropdown\" style=\"display: none;\"><div class=\"menu-item\" id=\"menu-new-tab\">New tab <span class=\"shortcut\">Ctrl+T</span></div><div class=\"menu-item\" id=\"menu-new-incognito\">New incognito tab</div><div class=\"menu-divider\"></div><div class=\"menu-item\" id=\"menu-reload\">Reload</div><div class=\"menu-item\" id=\"menu-bookmark\">Bookmark this tab</div><div class=\"menu-divider\"></div><div class=\"menu-item\" id=\"menu-history\">History</div><div class=\"menu-item\" id=\"menu-settings\">Settings</div><div class=\"menu-divider\"></div><div class=\"menu-item\" id=\"menu-exit\">Exit Browser</div></div></div></div><div class=\"browser-bookmarks-bar\" id=\"browser-bookmarks-bar\"></div><div class=\"browser-progress-bar-container\"><div class=\"browser-progress-bar\" id=\"browser-progress-bar\" style=\"width: 0%;\"></div></div><div class=\"browser-viewport\" id=\"browser-viewport\"><div class=\"modal-loader\" id=\"reader-modal-loader\" style=\"display: none;\"><div class=\"modal-spinner\"></div><span style=\"color: var(--text-muted);\">Routing through secure onion circuits...</span></div><div id=\"reader-modal-content\"></div></div></div>";
    set_prop(readerModal, "innerHTML", readerModalHtml);
    document.body.appendChild(readerModal);
    window.browserTabs = [];
    window.activeTabId = "";
    window.browserBookmarks = [];
    ddgBookmark = Object();
    ddgBookmark.title = "DuckDuckGo";
    ddgBookmark.url = "https://html.duckduckgo.com/html/";
    window.browserBookmarks.push(ddgBookmark);
    wikiBookmark = Object();
    wikiBookmark.title = "Wikipedia";
    wikiBookmark.url = "https://www.wikipedia.org";
    window.browserBookmarks.push(wikiBookmark);
    torBookmark = Object();
    torBookmark.title = "Tor Project";
    torBookmark.url = "https://www.torproject.org";
    window.browserBookmarks.push(torBookmark);
    btnCloseBrowser = document.getElementById("btn-close-browser");
    if (btnCloseBrowser) {
        btnCloseBrowser.addEventListener("click", (event) => {
    modal = document.getElementById("reader-view-modal");
    modal.classList.remove("active");
});
    }
    btnAddTab = document.getElementById("btn-browser-add-tab");
    if (btnAddTab) {
        btnAddTab.addEventListener("click", (event) => {
    createBrowserTab("ernos://newtab", true);
});
    }
    btnBack = document.getElementById("btn-browser-back");
    if (btnBack) {
        btnBack.addEventListener("click", (event) => {
    activeTab = getActiveTab();
    if ((activeTab && (activeTab.historyIndex > 0))) {
        activeTab.historyIndex = (activeTab.historyIndex - 1);
        url = Reflect.get(activeTab.history, activeTab.historyIndex);
        navigateActiveTab(url, true);
    }
});
    }
    btnForward = document.getElementById("btn-browser-forward");
    if (btnForward) {
        btnForward.addEventListener("click", (event) => {
    activeTab = getActiveTab();
    if ((activeTab && (activeTab.historyIndex < (activeTab.history.length - 1)))) {
        activeTab.historyIndex = (activeTab.historyIndex + 1);
        url = Reflect.get(activeTab.history, activeTab.historyIndex);
        navigateActiveTab(url, true);
    }
});
    }
    btnReload = document.getElementById("btn-browser-reload");
    if (btnReload) {
        btnReload.addEventListener("click", (event) => {
    activeTab = getActiveTab();
    if (activeTab) {
        navigateActiveTab(activeTab.url, true);
    }
});
    }
    btnHome = document.getElementById("btn-browser-home");
    if (btnHome) {
        btnHome.addEventListener("click", (event) => {
    navigateActiveTab("ernos://newtab");
});
    }
    addressInput = document.getElementById("browser-address-input");
    if (addressInput) {
        addressInput.addEventListener("keydown", (event) => {
    if ((event.key === "Enter")) {
        navigateActiveTab(addressInput.value, false);
    }
});
    }
    btnStar = document.getElementById("btn-browser-star");
    if (btnStar) {
        btnStar.addEventListener("click", (event) => {
    toggleBookmarkActiveTab();
});
    }
    btnMenu = document.getElementById("btn-browser-menu");
    if (btnMenu) {
        btnMenu.addEventListener("click", (event) => {
    event.stopPropagation();
    dropdown = document.getElementById("browser-menu-dropdown");
    if (dropdown) {
        if ((dropdown.style.show === "none")) {
            set_prop(dropdown.style, "display", "block");
        } else {
            set_prop(dropdown.style, "display", "none");
        }
    }
});
    }
    document.addEventListener("click", (event) => {
    dropdown = document.getElementById("browser-menu-dropdown");
    if (dropdown) {
        set_prop(dropdown.style, "display", "none");
    }
});
    menuNewTab = document.getElementById("menu-new-tab");
    if (menuNewTab) {
        menuNewTab.addEventListener("click", (event) => {
    createBrowserTab("ernos://newtab", true);
});
    }
    menuNewIncognito = document.getElementById("menu-new-incognito");
    if (menuNewIncognito) {
        menuNewIncognito.addEventListener("click", (event) => {
    createBrowserTab("ernos://newtab", true);
});
    }
    menuReloadOption = document.getElementById("menu-reload");
    if (menuReloadOption) {
        menuReloadOption.addEventListener("click", (event) => {
    activeTab = getActiveTab();
    if (activeTab) {
        navigateActiveTab(activeTab.url, true);
    }
});
    }
    menuBookmarkOption = document.getElementById("menu-bookmark");
    if (menuBookmarkOption) {
        menuBookmarkOption.addEventListener("click", (event) => {
    toggleBookmarkActiveTab();
});
    }
    menuExitOption = document.getElementById("menu-exit");
    if (menuExitOption) {
        menuExitOption.addEventListener("click", (event) => {
    modal = document.getElementById("reader-view-modal");
    modal.classList.remove("active");
});
    }
    renderBookmarksBar();
    onionForm = document.getElementById("onion-search-form");
    if (onionForm) {
        onionForm.addEventListener("submit", (event) => {
    event.preventDefault();
    engineSelect = document.getElementById("onion-engine");
    queryInput = document.getElementById("onion-query-input");
    engine = engineSelect.value;
    query = queryInput.value;
    circuitContainer = document.getElementById("onion-circuit-container");
    set_prop(circuitContainer.style, "display", "block");
    pulse1 = document.getElementById("pulse-1");
    pulse2 = document.getElementById("pulse-2");
    pulse3 = document.getElementById("pulse-3");
    set_prop(pulse1.style, "display", "none");
    set_prop(pulse2.style, "display", "none");
    set_prop(pulse3.style, "display", "none");
    resultsBox = document.getElementById("onion-results-box");
    set_prop(resultsBox, "innerHTML", "<div style='color: var(--text-muted); text-align: center; padding: 20px 0;'><div class='modal-spinner' style='width:24px; height:24px; margin:0 auto 10px auto;'></div>Routing encrypted packet through onion hops...</div>");
    setTimeout((dummy) => {
    set_prop(pulse1.style, "display", "block");
    anim1 = document.getElementById("anim-1");
    anim1.beginElement();
    setTimeout((dummy2) => {
    set_prop(pulse2.style, "display", "block");
    anim2 = document.getElementById("anim-2");
    anim2.beginElement();
    setTimeout((dummy3) => {
    set_prop(pulse3.style, "display", "block");
    anim3 = document.getElementById("anim-3");
    anim3.beginElement();
    searchMsg = Object();
    searchMsg.type = "onion_search";
    searchMsg.engine = engine;
    searchMsg.query = query;
    send_msg(window.ws, JSON.stringify(searchMsg));
}, 400);
}, 300);
}, 300);
});
    }
    window.onionViewPage = (viewUrl) => {
    modal = document.getElementById("reader-view-modal");
    modal.classList.add("active");
    createBrowserTab(viewUrl, true);
};
    navItems = document.querySelectorAll(".nav-item");
    tabPanels = document.querySelectorAll(".tab-panel");
    pageTitle = document.getElementById("page-title");
    navItems.forEach((item) => {
    item.addEventListener("click", (event) => {
    targetTab = item.getAttribute("data-tab");
    window.localStorage.setItem("ernode_active_tab", targetTab);
    navItems.forEach((n) => {
    n.classList.remove("active");
});
    tabPanels.forEach((p) => {
    p.classList.remove("active");
});
    item.classList.add("active");
    targetPanel = document.getElementById(("tab-" + String(targetTab)));
    targetPanel.classList.add("active");
    pageTitle.textContent = item.textContent.trim();
    if ((targetTab === "messaging")) {
        renderChatHistory(window.activeChannel);
    } else if ((targetTab === "ai")) {
        renderAiHistory();
    } else if ((targetTab === "guide")) {
        navList = document.getElementById("guide-nav-list");
        if (navList) {
            activeBtn = navList.querySelector("button.active");
            if (activeBtn) {
                file = activeBtn.getAttribute("data-guide-file");
                msg = Object();
                msg.type = "gitdec_get_repo_file";
                msg.repo_id = "ErnosDecent";
                msg.filename = file;
                send_msg(window.ws, JSON.stringify(msg));
            }
        }
    }
    if ((window.isConnected && window.ws)) {
        if ((targetTab === "agent-memory")) {
            msg = Object();
            msg.type = "get_agent_memory";
            send_msg(window.ws, JSON.stringify(msg));
            setTimeout((dummy) => {
    initMemoryCanvas();
}, 50);
        } else if ((targetTab === "turing-grid")) {
            msg = Object();
            msg.type = "get_turing_grid";
            send_msg(window.ws, JSON.stringify(msg));
        } else if ((targetTab === "gitdec")) {
            msg = Object();
            msg.type = "gitdec_get_repos";
            send_msg(window.ws, JSON.stringify(msg));
        }
    }
});
});
    setInterval((dummy) => {
    if (window.isConnected) {
        window.uptimeSeconds = (window.uptimeSeconds + 1);
        hours = Math.floor((window.uptimeSeconds / 3600)).toString().padStart(2, "0");
        minutes = Math.floor(((window.uptimeSeconds % 3600) / 60)).toString().padStart(2, "0");
        seconds = (window.uptimeSeconds % 60).toString().padStart(2, "0");
        nodeUptime = document.getElementById("node-uptime");
        nodeUptime.textContent = ((((String(hours) + ":") + String(minutes)) + ":") + String(seconds));
    }
}, 1000);
    setInterval((dummy) => {
    if ((window.isConnected && window.ws)) {
        msgStatus = Object();
        msgStatus.type = "get_status";
        send_msg(window.ws, JSON.stringify(msgStatus));
        msgWallet = Object();
        msgWallet.type = "get_wallet";
        send_msg(window.ws, JSON.stringify(msgWallet));
        msgStorage = Object();
        msgStorage.type = "get_storage";
        send_msg(window.ws, JSON.stringify(msgStorage));
        msgPool = Object();
        msgPool.type = "get_pool";
        send_msg(window.ws, JSON.stringify(msgPool));
        msgMemory = Object();
        msgMemory.type = "get_agent_memory";
        send_msg(window.ws, JSON.stringify(msgMemory));
        msgTuring = Object();
        msgTuring.type = "get_turing_grid";
        send_msg(window.ws, JSON.stringify(msgTuring));
        msgModels = Object();
        msgModels.type = "get_ai_models";
        send_msg(window.ws, JSON.stringify(msgModels));
        msgHosts = Object();
        msgHosts.type = "dht_get";
        msgHosts.key = "network:host_nodes";
        send_msg(window.ws, JSON.stringify(msgHosts));
    }
}, 10000);
    transferForm = document.getElementById("transfer-form");
    transferForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!window.isConnected) {
        return 0;
    }
    recipient = window.recipientDidInput.value;
    amount = parseFloat(window.transferAmountInput.value);
    if ((isNaN(amount) || (amount <= 0))) {
        return 0;
    }
    msg = Object();
    msg.type = "transfer";
    set_prop(msg, "to", recipient);
    msg.amount = amount.toString();
    send_msg(window.ws, JSON.stringify(msg));
    window.recipientDidInput.value = "";
    window.transferAmountInput.value = "";
});
    window.swapFromAmount.addEventListener("input", (event) => {
    val = parseFloat(window.swapFromAmount.value);
    if ((isNaN(val) || (val <= 0))) {
        window.swapToAmount.value = "";
    } else {
        window.swapToAmount.value = "N/A";
    }
});
    btnSwapTokens = document.getElementById("btn-swap-tokens");
    btnSwapTokens.addEventListener("click", (event) => {
    if (!window.isConnected) {
        return 0;
    }
    fromVal = parseFloat(window.swapFromAmount.value);
    if ((isNaN(fromVal) || (fromVal <= 0))) {
        return 0;
    }
    msg = Object();
    msg.type = "swap";
    msg.from_token = document.getElementById("swap-from-token").value;
    msg.to_token = document.getElementById("swap-to-token").value;
    msg.amount = fromVal.toString();
    send_msg(window.ws, JSON.stringify(msg));
    window.swapFromAmount.value = "";
    window.swapToAmount.value = "";
});
    chatForm = document.getElementById("chat-send-form");
    chatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    text = window.chatInput.value.trim();
    if ((!text || !window.isConnected)) {
        return 0;
    }
    appendMessage(window.chatContainer, "You", text, "sent");
    window.chatInput.value = "";
    msg = Object();
    msg.type = "send_chat";
    msg.text = text;
    send_msg(window.ws, JSON.stringify(msg));
});
    aiForm = document.getElementById("ai-send-form");
    aiForm.addEventListener("submit", (event) => {
    event.preventDefault();
    prompt = window.aiInput.value.trim();
    if ((!prompt || !window.isConnected)) {
        return 0;
    }
    appendMessage(window.aiContainer, "You", prompt, "sent");
    window.aiInput.value = "";
    set_prop(window.aiLoader.style, "display", "flex");
    window.aiInput.disabled = true;
    btnSubmit = document.getElementById("btn-submit-ai");
    btnSubmit.disabled = true;
    stopBtn = document.getElementById("btn-stop-ai");
    if ((stopBtn !== 0)) {
        stopBtn.disabled = false;
        stopBtn.textContent = "Stop";
        set_prop(stopBtn.style, "display", "inline-block");
    }
    msg = Object();
    msg.type = "ai_prompt";
    msg.prompt = prompt;
    msg.system = window.aiSystemPrompt.value;
    msg.model = window.selectedAiModel;
    send_msg(window.ws, JSON.stringify(msg));
});
    channelBtns = document.querySelectorAll("[data-channel]");
    channelBtns.forEach((btn) => {
    btn.addEventListener("click", (event) => {
    channelName = btn.getAttribute("data-channel");
    window.activeChannel = channelName;
    channelBtns.forEach((b) => {
    b.classList.remove("active");
});
    btn.classList.add("active");
    renderChatHistory(channelName);
});
});
    aiModelSelect = document.getElementById("ai-model-select");
    if (aiModelSelect) {
        aiModelSelect.addEventListener("change", (event) => {
    selectAiModel(event.target.value, false);
});
    }
    if (window.aiModelsListContainer) {
        window.aiModelsListContainer.addEventListener("click", (event) => {
    btn = event.target.closest("[data-model]");
    if (btn) {
        modelName = btn.getAttribute("data-model");
        selectAiModel(modelName, false);
    }
});
    }
    btnRefreshHosts = document.getElementById("btn-refresh-hosts");
    if (btnRefreshHosts) {
        btnRefreshHosts.addEventListener("click", (event) => {
    if ((window.isConnected && window.ws)) {
        msgHosts = Object();
        msgHosts.type = "dht_get";
        msgHosts.key = "network:host_nodes";
        send_msg(window.ws, JSON.stringify(msgHosts));
    }
});
    }
    dhtForm = document.getElementById("dht-form");
    if (dhtForm) {
        dhtForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!window.isConnected) {
        return 0;
    }
    action = document.getElementById("dht-action").value;
    key = document.getElementById("dht-key-input").value.trim();
    if (!key) {
        return 0;
    }
    if ((action === "store")) {
        val = document.getElementById("dht-value-input").value.trim();
        if (!val) {
            return 0;
        }
        msg = Object();
        msg.type = "dht_store";
        msg.key = key;
        msg.value = val;
        send_msg(window.ws, JSON.stringify(msg));
    } else {
        msg = Object();
        msg.type = "dht_get";
        msg.key = key;
        send_msg(window.ws, JSON.stringify(msg));
    }
});
    }
    nameForm = document.getElementById("name-form");
    if (nameForm) {
        nameForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!window.isConnected) {
        return 0;
    }
    action = document.getElementById("name-action").value;
    name = document.getElementById("name-input").value.trim();
    if (!name) {
        return 0;
    }
    window.localStorage.setItem("ernode_last_name", name);
    if ((action === "register")) {
        msg = Object();
        msg.type = "name_register";
        msg.name = name;
        send_msg(window.ws, JSON.stringify(msg));
        setTimeout((dummy) => {
    msgId = Object();
    msgId.type = "get_identity";
    send_msg(window.ws, JSON.stringify(msgId));
}, 800);
    } else {
        msg = Object();
        msg.type = "name_resolve";
        msg.name = name;
        send_msg(window.ws, JSON.stringify(msg));
    }
});
    }
    btnDecayMemory = document.getElementById("btn-decay-memory");
    if (btnDecayMemory) {
        btnDecayMemory.addEventListener("click", (event) => {
    if (!window.isConnected) {
        return 0;
    }
    msg = Object();
    msg.type = "decay_memory";
    send_msg(window.ws, JSON.stringify(msg));
});
    }
    turingForm = document.getElementById("turing-form");
    if (turingForm) {
        turingForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!window.isConnected) {
        return 0;
    }
    action = document.getElementById("turing-action").value;
    args = document.getElementById("turing-args").value.trim();
    cmdStr = (((("Action: turing_grid_op([\"" + String(action)) + "\", \"") + String(args)) + "\"])");
    if (((action === "read") || (action === "execute"))) {
        cmdStr = (("Action: turing_grid_op([\"" + String(action)) + "\", \"\"])");
    }
    turingLog = document.getElementById("turing-log");
    entry = document.createElement("div");
    entry.className = "turing-log-entry";
    entry.textContent = (("Running: " + String(cmdStr)) + "...");
    turingLog.appendChild(entry);
    turingLog.scrollTop = turingLog.scrollHeight;
    msg = Object();
    msg.type = "ai_prompt";
    msg.prompt = cmdStr;
    msg.system = "Execute the tool action directly.";
    send_msg(window.ws, JSON.stringify(msg));
    setTimeout((dummy) => {
    msgGrid = Object();
    msgGrid.type = "get_turing_grid";
    send_msg(window.ws, JSON.stringify(msgGrid));
}, 1200);
});
    }
    btnTriggerAutonomy = document.getElementById("btn-trigger-autonomy");
    if (btnTriggerAutonomy) {
        btnTriggerAutonomy.addEventListener("click", (event) => {
    if (!window.isConnected) {
        return 0;
    }
    set_prop(window.aiLoader.style, "display", "flex");
    msg = Object();
    msg.type = "run_autonomy_agent";
    send_msg(window.ws, JSON.stringify(msg));
});
    }
    guideBtns = document.querySelectorAll(".guide-menu-item");
    guideSections = document.querySelectorAll(".guide-section");
    guideBtns.forEach((btn) => {
    btn.addEventListener("click", (event) => {
    targetGuide = btn.getAttribute("data-guide");
    guideBtns.forEach((b) => {
    b.classList.remove("active");
});
    guideSections.forEach((s) => {
    s.classList.remove("active");
});
    btn.classList.add("active");
    targetSec = document.getElementById(("guide-" + String(targetGuide)));
    if (targetSec) {
        targetSec.classList.add("active");
    }
});
});
    btnNewSession = document.getElementById("btn-new-session");
    if (btnNewSession) {
        btnNewSession.addEventListener("click", (event) => {
    newId = ("session_" + String(Date.now()));
    newTitle = prompt("Enter session title:", "New Session");
    if ((!newTitle || (newTitle.trim().length === 0))) {
        return 0;
    }
    msg = Object();
    msg.type = "session_new";
    msg.id = newId;
    msg.title = newTitle.trim();
    msg.model = (window.selectedAiModel || "");
    msg.system = window.aiSystemPrompt.value;
    send_msg(window.ws, JSON.stringify(msg));
});
    }
    btnSaveDiscord = document.getElementById("btn-save-discord");
    if (btnSaveDiscord) {
        btnSaveDiscord.addEventListener("click", (event) => {
    savePlatformConfig("discord");
});
    }
    toggleDiscord = document.getElementById("toggle-discord");
    if (toggleDiscord) {
        toggleDiscord.addEventListener("change", (event) => {
    handlePlatformToggle("discord");
});
    }
    btnSaveWhatsapp = document.getElementById("btn-save-whatsapp");
    if (btnSaveWhatsapp) {
        btnSaveWhatsapp.addEventListener("click", (event) => {
    savePlatformConfig("whatsapp");
});
    }
    toggleWhatsapp = document.getElementById("toggle-whatsapp");
    if (toggleWhatsapp) {
        toggleWhatsapp.addEventListener("change", (event) => {
    handlePlatformToggle("whatsapp");
});
    }
    btnSaveTelegram = document.getElementById("btn-save-telegram");
    if (btnSaveTelegram) {
        btnSaveTelegram.addEventListener("click", (event) => {
    savePlatformConfig("telegram");
});
    }
    toggleTelegram = document.getElementById("toggle-telegram");
    if (toggleTelegram) {
        toggleTelegram.addEventListener("change", (event) => {
    handlePlatformToggle("telegram");
});
    }
    btnAddPlugin = document.getElementById("btn-add-plugin");
    if (btnAddPlugin) {
        btnAddPlugin.addEventListener("click", (event) => {
    registerPlugin();
});
    }
    btnSavePrompts = document.getElementById("btn-save-prompts");
    if (btnSavePrompts) {
        btnSavePrompts.addEventListener("click", (event) => {
    savePromptsConfig();
});
    }
    btnSaveSystemConfig = document.getElementById("btn-save-system-config");
    if (btnSaveSystemConfig) {
        btnSaveSystemConfig.addEventListener("click", (event) => {
    saveSystemConfig();
});
    }
    subTabs = document.querySelectorAll(".settings-tab-btn");
    if (subTabs) {
        subTabs.forEach((tab) => {
    tab.addEventListener("click", (event) => {
    subTabs.forEach((t) => {
    t.classList.remove("active");
});
    tab.classList.add("active");
    tabContents = document.querySelectorAll(".settings-tab-content");
    if (tabContents) {
        tabContents.forEach((content) => {
    ok = set_prop(content.style, "display", "none");
    content.classList.remove("active");
});
    }
    tabAttr = tab.getAttribute("data-settings-tab");
    targetId = ("settings-" + tabAttr);
    targetEl = document.getElementById(targetId);
    if (targetEl) {
        ok = set_prop(targetEl.style, "display", "block");
        targetEl.classList.add("active");
    }
});
});
    }
    initGitDec();
    initGuide();
    handleDisconnect();
    connectDaemon();
    renderChatHistory(window.activeChannel);
    savedLastName = window.localStorage.getItem("ernode_last_name");
    if (savedLastName) {
        nameInput = document.getElementById("name-input");
        if ((nameInput && !nameInput.value)) {
            nameInput.value = savedLastName;
        }
    }
    savedTab = window.localStorage.getItem("ernode_active_tab");
    if (savedTab) {
        targetBtn = document.querySelector(((".nav-item[data-tab='" + String(savedTab)) + "']"));
        if (targetBtn) {
            clickFn = targetBtn["click"];
            clickFn.call(targetBtn);
        }
    }
    window.activeSessionId = "default";
    return 0;
}

main();
