"use strict";

const fs = require("fs");
const vm = require("vm");

const sourcePath = process.argv[2] || "decent_web/app.js";
const source = fs.readFileSync(sourcePath, "utf8");
const start = source.indexOf("function deliveryReceiptIdValid(");
const end = source.indexOf("\nfunction handleDaemonMessage(", start);
if (start < 0 || end < 0) {
    throw new Error("compiled WebUI receipt functions were not found");
}

const storage = new Map();
const sent = [];
const applied = [];
const reported = [];
let closed = 0;
const context = {
    JSON,
    Object,
    console,
    window: {
        currentInboundDeliveryId: "",
        currentInboundDeliveryDuplicate: false,
        inboundDeliveryBuffer: [],
        localStorage: {
            getItem(key) {
                return storage.has(key) ? storage.get(key) : null;
            },
            setItem(key, value) {
                storage.set(key, String(value));
            },
        },
        ws: {
            readyState: 1,
            send(payload) {
                sent.push(JSON.parse(payload));
            },
            close() {
                closed += 1;
            },
        },
    },
    substring(value, offset, length) {
        return value.substring(offset, offset + length);
    },
    string_index_of(value, needle) {
        return value.indexOf(needle);
    },
    get_list(value, key) {
        return value[key];
    },
    send_msg(ws, payload) {
        if (!ws || ws.readyState !== 1) return 0;
        ws.send(payload);
        return 1;
    },
    handleDaemonMessage(message) {
        applied.push(message);
        return 1;
    },
    reportClientError(message) {
        reported.push(String(message));
        return 0;
    },
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context, { filename: sourcePath });

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

assert(!source.includes('set_prop(window.ws, "send"'),
       "approval controls overwrite the WebSocket send method");
for (const messageName of ["approveMsg", "approveAllMsg", "denyMsg"]) {
    assert(source.includes(`send_msg(window.ws, ${messageName})`),
           `${messageName} does not use the checked WebSocket sender`);
}

const receipt = `outbox:17:${"a".repeat(64)}`;
const content = { type: "ai_token", token: "received once" };
assert(context.deliveryReceiptIdValid(receipt) === 1, "stable receipt rejected");
assert(context.handleIncomingDaemonMessage({ type: "delivery_begin", delivery_id: receipt }) === 1,
       "delivery_begin failed");
assert(context.handleIncomingDaemonMessage(content) === 1, "delivery content failed");
assert(applied.length === 0, "content was applied before delivery_commit");
assert(context.handleIncomingDaemonMessage({ type: "delivery_commit", delivery_id: receipt }) === 1,
       "delivery_commit failed");
assert(applied.length === 1, "committed content was not applied exactly once");
assert(sent.length === 1 && sent[0].type === "delivery_ack" && sent[0].delivery_id === receipt,
       "browser ACK did not follow application and receipt persistence");
assert(context.deliveryReceiptSeen(receipt) === 1, "durable browser receipt was not recorded");

// Model a server crash after the browser ACK but before the database transition.
// Recovery resends the same stable ID. The browser ACKs it without re-applying.
context.handleIncomingDaemonMessage({ type: "delivery_begin", delivery_id: receipt });
context.handleIncomingDaemonMessage(content);
context.handleIncomingDaemonMessage({ type: "delivery_commit", delivery_id: receipt });
assert(applied.length === 1, "crash recovery duplicated an acknowledged delivery");
assert(sent.length === 2 && sent[1].delivery_id === receipt,
       "idempotent recovery did not return a second exact ACK");

const otherReceipt = `trace:9:${"b".repeat(64)}`;
context.handleIncomingDaemonMessage({ type: "delivery_begin", delivery_id: otherReceipt });
assert(context.handleIncomingDaemonMessage({ type: "delivery_commit", delivery_id: receipt }) === 0,
       "mismatched commit was accepted");
assert(closed === 1, "mismatched commit did not close the protocol session");
assert(reported.length === 1 && reported[0].includes("does not match"),
       "mismatched commit failure was not made visible");

for (let i = 1; i <= 700; i += 1) {
    const id = `trace:${i}:${i.toString(16).padStart(64, "0")}`;
    assert(context.recordDeliveryReceipt(id) === 1, `receipt ${i} was not recorded`);
}
const history = storage.get("ernos_webui_delivery_receipts");
assert(history.length < 60000, "browser receipt history is not bounded");
assert(context.deliveryReceiptSeen(`trace:700:${(700).toString(16).padStart(64, "0")}`) === 1,
       "newest bounded receipt was lost");

console.log("WebUI delivery receipt JS: protocol checks and 700-entry bound passed");
