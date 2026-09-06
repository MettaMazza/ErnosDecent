"use strict";

const fs = require("fs");
const vm = require("vm");

const sourcePath = process.argv[2] || "decent_web/app.js";
const source = fs.readFileSync(sourcePath, "utf8");
const start = source.indexOf("function set_prop(");
const end = source.indexOf("\nfunction attachTtsButton(", start);
if (start < 0 || end < 0) {
    throw new Error("compiled WebUI TTS functions were not found");
}

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

const sent = [];
const audios = [];
const context = {
    Reflect,
    Object,
    JSON,
    console,
    window: {
        isConnected: true,
        ttsRequestCounter: 0,
        pendingTtsRequests: {},
        pendingTtsOrder: [],
        ws: {
            readyState: 1,
            send(payload) {
                sent.push(JSON.parse(payload));
            },
        },
    },
    document: {
        createElement(kind) {
            assert(kind === "audio", "TTS created a non-audio element");
            const audio = {
                src: "",
                playCount: 0,
                pauseCount: 0,
                loadCount: 0,
                play() { this.playCount += 1; },
                pause() { this.pauseCount += 1; },
                removeAttribute(name) {
                    assert(name === "src", "TTS removed the wrong audio attribute");
                    this.src = "";
                },
                load() { this.loadCount += 1; },
            };
            audios.push(audio);
            return audio;
        },
    },
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context, { filename: sourcePath });

const button = {
    disabled: false,
    textContent: "🔊",
    title: "",
    ttsState: "ready",
    ttsUrl: null,
    ttsAudio: null,
    ttsRequestId: null,
};

context.requestTts("A single voice", button);
context.requestTts("A single voice", button);
assert(sent.length === 1, "a repeated pending click sent a second synthesis request");
assert(button.ttsState === "pending" && button.disabled,
       "the button was not locked while synthesis was pending");
assert(sent[0].request_id === "tts-1", "the synthesis request was not correlated");

context.handleTtsReady({
    type: "tts_ready",
    request_id: "tts-1",
    url: "/tts/cached.wav",
});
assert(audios.length === 1 && audios[0].playCount === 1,
       "the first ready response did not play exactly once");
assert(button.ttsState === "delivered", "the delivered state was not recorded");

context.requestTts("A single voice", button);
assert(button.ttsState === "cached", "the second completed click did not remove playback");
assert(audios[0].pauseCount === 1 && audios[0].loadCount === 1 && audios[0].src === "",
       "the prior WebUI audio was not stopped and released");

context.requestTts("A single voice", button);
assert(sent.length === 1, "cached replay issued another synthesis request");
assert(audios.length === 2 && audios[1].src === "/tts/cached.wav" && audios[1].playCount === 1,
       "cached replay did not redeliver the existing audio URL");
assert(button.ttsState === "delivered", "cached replay did not restore delivered state");

const legacyButton = {
    disabled: false,
    textContent: "🔊",
    title: "",
    ttsState: "ready",
    ttsUrl: null,
    ttsAudio: null,
    ttsRequestId: null,
};
context.requestTts("Rollout compatibility", legacyButton);
context.handleTtsReady({ type: "tts_ready", url: "/tts/legacy.wav" });
assert(legacyButton.ttsState === "delivered" && legacyButton.ttsUrl === "/tts/legacy.wav",
       "a response from the already-running pre-correlation server was lost");

console.log("WebUI TTS single-flight, remove, and cached replay checks passed");
