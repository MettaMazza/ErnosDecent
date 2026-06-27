# ErnosPlain — A Programming Language That Reads Like English

*Phase A2 reader-analyst notes. Plain-language characterisation for a general-audience book.
Sources: `/Users/mettamazza/Desktop/ErnosPlain Programing Language/` — README.md,
LANGUAGE_REFERENCE.md, demos/.*

---

## What ErnosPlain is

ErnosPlain (the language is called "Ernos"; source files end in `.ep`) is a **programming language
whose code is written in plain English sentences** instead of the dense symbols most programming
languages use. It is the language Maria built her decentralized system (ErnosDecent) in.

> "A compiled language with plain English syntax … and C-level performance."
> — `/Users/mettamazza/Desktop/ErnosPlain Programing Language/README.md`, line 3

> "Ernos is a … programming language that reads like plain English."
> — `README.md`, line 18

Its own tagline sums up the goal:

> "Code that reads like English. Runs like C."
> — `README.md`, line 406

---

## How it reads (a tiny real example, contrasted with conventional code)

Here is a real, complete ErnosPlain program from the README — a function that multiplies a number
by itself down to 1 (a "factorial"):

```ernos
define factorial with n as Int returning Int:
    if n < 2:
        return 1
    return n * factorial(n - 1)

define main:
    display "Factorial of 20:"
    display factorial(20)
    return 0
```
— `/Users/mettamazza/Desktop/ErnosPlain Programing Language/README.md`, lines 21–30

Read aloud, it is almost ordinary English: *"define factorial with n as a whole number, returning a
whole number: if n is less than 2, return 1…"* You **set** a variable "to" a value, you **display**
things, you **define** a function "with" its inputs.

Compare the same idea in a conventional language like C or Java, which a newcomer cannot read aloud:

```c
int factorial(int n) {
    if (n < 2) return 1;
    return n * factorial(n - 1);
}
```

The curly braces, semicolons and terse type names are exactly the "noise" Ernos removes. As the
README puts it:

> "**No curly braces. No semicolons. No noise.** Just code that reads like instructions."
> — `README.md`, line 32

Other everyday-English constructs (all verifiable in README.md / LANGUAGE_REFERENCE.md):
`set x to 42`, `for each item in list:`, `repeat while cond:`, `send value to ch`,
`set v to receive from ch`, `spawn worker(...)`. Conditions can be written `equals`, `is not equal
to`, `and also`, `or else`. The structure uses indentation (like Python) rather than braces
(LANGUAGE_REFERENCE.md, lines 30–43).

---

## Why a plain-English language is a philosophical, anti-gatekeeping act

For the book's argument, this is the key point. Programming has always been guarded by a wall of
symbols and jargon that you must be trained (usually formally) to read. A language anyone can read
aloud tears that wall down. It says: *you do not need a computer-science degree, or permission, to
instruct a machine.*

This is the same anti-gatekeeping move as the Fold theory (truth anyone can verify) and the Seed
Vault (knowledge with "no mythological access barriers"). ErnosPlain is that principle applied to
the act of *building* — it lowers the barrier to creating software to the barrier of writing a clear
sentence. It is especially pointed coming from a self-taught maker with no formal coding background
(see the story notes): she built the tool she herself needed to cross that wall, then built her whole
decentralized internet *in it.*

The deeper resonance: a language is power over machines. Putting that power in plain language is
putting it back in ordinary people's hands — decentralizing capability itself, not just servers.

---

## Technical facts that appear TRUE from the files (with caveats)

These are stated in the project's own docs; presented here as the project's claims that are at least
internally consistent and partly checkable from the repo contents:

- **Compiles to C, then to a native binary.** The pipeline is Source → Lexer → Parser → Type checker
  → Borrow checker → Optimizer → C source → `clang -O2` → native binary
  (`README.md`, lines 18, 49, 277–293). C source files (`*_compiled.c`) and compiled binaries (e.g.
  `borrow_param_valid`, `creature_quest`) are present in the directory, consistent with this.
- **Aims at C-level performance** — "no interpreter overhead … runs at the same speed as equivalent C"
  (`README.md`, line 49).
- **Statically typed with safety checks** — type inference (Hindley-Milner-style unification),
  ownership/borrow checking similar to Rust's, and Send/Sync thread-safety (README.md, lines 56–69).
- **Self-hosting** — i.e. the compiler is partly written in its own language. The README lists a
  self-hosted compiler (`ep_lexer.ep`, `ep_parser.ep`, `ep_codegen.ep`, `epc.ep`, ~5,824 lines of
  ErnosPlain; README.md, lines 329–347). Large `.ep` compiler sources (`ep_codegen.ep` ~206 KB,
  `ep_parser`, etc.) and their generated `.c` files are physically present in the directory, consistent
  with a self-hosting compiler.
- **Broad standard library and FFI** — ~24 stdlib modules and ~29 C-library bindings (raylib, sqlite,
  openssl, libsodium, curl, etc.; README.md, lines 76–110), plus tooling (REPL, formatter, LSP, WASM
  target, transpilers from Python/C/JS/Go/Rust/Java/TS/Ruby into ErnosPlain; lines 112–131).

**Caveat for honesty:** the bootstrap compiler is built with Rust/cargo (README.md, lines 142–151),
and some build/maturity notes elsewhere indicate rough edges (e.g. internal memory notes mention a
"node build ships stale binary" issue and that whole-program type-checking can fail). The book should
say the language *exists, compiles real programs, and is self-hosting in substantial part* — which the
files support — without overclaiming flawless production-readiness. The headline badge is "Tests
51/51" (README.md, line 8), a modest figure; treat performance/maturity claims as the project's own.

---

## How it underpins ErnosDecent

ErnosDecent — Maria's decentralized internet/node software — is written in ErnosPlain (`.ep`). The
language is the foundation layer: the Fold theory is the worldview, ErnosPlain is the *tool*, and
ErnosDecent is what she builds *with* the tool. The reviewer's framing ties them together as one arc:
the theory of everything, the autonomous mind, "a language that reads like English," and "an internet
of one's own" (`/Users/mettamazza/Desktop/_REVIEW_DOCUMENTARY/BOOK_Behind_the_Creator.md`, lines
57–62). For the book: ErnosPlain is the bridge between the philosophy (anyone can verify, anyone can
build) and the running system that delivers it.
