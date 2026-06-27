## Appendix A — Run It Yourself

This whole book rests on one claim: that you do not have to believe it, because the thing is real and you
can run it. This appendix is the shortest honest path to doing exactly that. You do not need to be a
programmer to follow it, though a programmer will move faster. The system is young, so expect the texture
of something still being finished — but it builds, and it boots.

**What you need.** A computer running macOS or Linux. (Windows works today through the compatibility layer
called WSL2 — a small Linux inside Windows — with a native Windows version still ahead.) You
also need the Ernos language tool, which compiles the plain-English source, and one cryptography library
called libsodium. The project's README lists the exact, current commands, kept factual and up to date.

**The shape of it.** You fetch the code, you run one build command, and you start the node:

```
git clone https://github.com/MettaMazza/ErnosDecent
cd ErnosDecent
bash build.sh        # turns the plain-English source into a running program
./node               # starts your node
```

When the node starts, it prints what it is doing — bringing up its services, opening its network
listeners — and tells you the address of your dashboard. Open that address in an ordinary web browser
(it lives on your own machine, not out on the internet) and you will see your node: its identity, its
wallet, its messages, its AI, the health of its connections. Nothing on that page leaves your computer
unless you send it somewhere on purpose.

**The free edition and the business edition.** The same engine ships in two places: the main edition, and
a business edition on a separate public branch that is the same engine under a light cosmetic overlay
(see Chapter 27). Both are under the AGPL licence; both are yours to read, run, copy, and change.

**Reading it.** The point of the plain-English language is that you can open any file and read what it
does. If a claim in this book matters to you, find the file, read it, and check. That is not a figure of
speech. It is the whole design.

If something does not work on your machine, that is useful too — it is the kind of thing the project's
GitDec issue tracker exists for. A system no one owns is improved by the people who run it. That can be
you.
