"use strict";

const fs = require("fs");
const vm = require("vm");

const sourcePath = process.argv[2] || "decent_web/app.js";
const source = fs.readFileSync(sourcePath, "utf8");
const start = source.indexOf("function substring(");
const end = source.indexOf("\nfunction decodeHTMLEntities(", start);
if (start < 0 || end < 0) {
    throw new Error("compiled WebUI response-formatting functions were not found");
}

const context = {
    Reflect,
    window: { RegExp },
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context, { filename: sourcePath });

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

const corruptArrow = `Reasoning $${"\r"}ightarrow$ Action $${"\r"}ightarrow$ Observation`;
assert(context.normalizeAiText(corruptArrow) === "Reasoning → Action → Observation",
       "JSON carriage-return arrow corruption was not repaired");
assert(context.normalizeAiText("Think $\\rightarrow$ Act $\\Rightarrow$ Result") ===
       "Think → Act ⇒ Result",
       "escaped LaTeX arrows were not converted to readable Unicode");

const sample = [
    "**Who I Am**",
    "I am Echo, with `local` tools.",
    "",
    "### My Systems",
    "*   **Tiered Memory:** persistent context",
    "*   **The Loop:** Reasoning $\\rightarrow$ Action",
    "",
    "1. **Echo:** first",
    "2. **Solance:** second",
].join("\n");
const rendered = context.renderAiMarkdown(sample);
assert(rendered.includes("<p><strong>Who I Am</strong></p>"),
       "bold section title was not rendered");
assert(rendered.includes("<h3>My Systems</h3>"),
       "heading was not rendered");
assert(rendered.includes("<ul><li><strong>Tiered Memory:</strong> persistent context</li>"),
       "unordered list was not rendered");
assert(rendered.includes("<ol><li><strong>Echo:</strong> first</li>"),
       "ordered list was not rendered");
assert(rendered.includes("Reasoning → Action"),
       "arrow was not normalised inside formatted content");
assert(rendered.includes("<code>local</code>"),
       "inline code was not rendered");

const hostile = context.renderAiMarkdown("<img src=x onerror=alert(1)> **safe**");
assert(!hostile.includes("<img"), "model HTML was inserted into the page");
assert(hostile.includes("&lt;img src=x onerror=alert(1)&gt;"),
       "model HTML was not preserved as escaped text");
assert(hostile.includes("<strong>safe</strong>"),
       "safe Markdown stopped working beside escaped HTML");

const fenced = context.renderAiMarkdown("```js\nconst x = '<unsafe>';\n```");
assert(fenced === "<pre><code>const x = &#039;&lt;unsafe&gt;&#039;;\n</code></pre>",
       "fenced code was not escaped and rendered deterministically");

assert(source.includes("attachTtsButton(window.currentAiResponseBubble, aiText)"),
       "completed AI replies no longer receive their TTS button");
assert(source.includes("attachTtsButton(bubble, normalizeAiText(text))"),
       "restored AI history no longer receives its TTS button");
assert(source.includes("requestTts(text, btn)"),
       "TTS button no longer speaks the source reply text");

console.log("WebUI response formatting: Markdown, arrows, XSS, code, and TTS checks passed");
