## Chapter 21 — A Companion That Learns and Remembers

The companies built a mind that knows you better than your oldest friend, and they built it to belong to them.

In the last chapter you put a real mind on your own machine — a language model that runs under your roof and answers only to you. But the raw model you switched on there has a flaw you feel within minutes. It cannot remember you. Every time you speak to it, it starts over, blank, with no idea who you are or what you asked an hour ago. And it does one thing: it reads your words and blurts the most likely next words, all at once, in a single rush, with no pause to work anything through. It is a brilliant student who answers off the top of their head and forgets your name the moment you leave the room. That is not a companion. That is a parlour trick.

The companies solved this, and the way they solved it is the whole crime in miniature. They gave their assistant a memory — and then they kept it. Every word you type, every preference it learns, every shape of how you think, flows up to a machine you will never see and becomes a file on you, owned by them, mined to sell you things or to sell *you*, switched off the day they choose. They learned the most intimate truth about the age: the mind that remembers you is the mind that owns you. So they made sure the remembering happened on their ground, not yours.

This chapter is about taking that back. It is the part of ErnosDecent that turns the forgetful model from Chapter 20 into a companion — one that thinks before it speaks, remembers what it learns, and gets better at the things you do together — with every scrap of that memory living on your disk, serving you, kept from everyone else.

### The plain idea

There are two ideas here, and they are simpler than they sound.

The first is **thinking out loud, step by step, instead of all at once.** Rather than read your question and dump one answer, the companion works through it the way a careful person solves a hard problem: it has a thought about what to do next, it does one small thing — looks something up, runs one check, fetches one fact — it looks at what came back, and then it has its next thought. Think, act, look at the result, think again. It loops like that until the job is actually done, and only then does it speak. The answer is the end of a piece of work, not a reflex.

The second is **memory in layers, the way a person carries memory.** You do not have one kind of memory; you have several, and they do different jobs. You have a scratchpad in your head for the thing you are doing right this minute, wiped the moment you finish it. You have a diary of what actually happened, in order. You have lessons drawn from experience — "this approach works, that one burned me" — which you trust more the more often they hold. You have skills, the how-to of tasks you have done before, reused without rebuilding them from scratch. And you have a web of facts where related ideas are linked, and the links you walk often grow strong while the ones you never touch fade. The companion is built with all five. Not on a server. On your disk. Five kinds of memory, the way a mind keeps them, kept where a mind should keep them — yours.

### An everyday picture

Picture a good assistant at a desk in your own house, and look at what is on and around that desk.

There is the **desk surface** itself, covered in sticky notes for today's task — phone numbers, half-finished sums, a reminder to call back at three. When the task is done, the notes go in the bin. That is the scratchpad: fast, temporary, gone when the goal is met.

There is a **diary** in the drawer, where the day's events are written in the order they happened. Nothing is interpreted; it is the record — at ten you asked this, at eleven the companion did that. That is the timeline.

There is a **filing cabinet** of lessons learned, each one a card that says "when this happens, do this — it has worked before," and each card carries a note of how sure the companion is, raised every time the lesson proves out. That is the lessons tier.

There is a **recipe box** of procedures — the steps for jobs done so often they have a saved method, with version notes in the margin: "method three is the good one; method four was worse, threw it out." That is procedural memory.

And there is a **map pinned to the wall**, a web of dots and lines, where every dot is an idea and every line joins two ideas that belong together. The lines you trace often get drawn darker; the ones you ignore fade to nothing. It is a footpath worn across a field — walk it daily and it becomes a clear trail; stop walking it and the grass grows back. That is the knowledge graph.

Five kinds of memory, one companion, all of it sitting on your desk, in your house, behind your door. Now picture the same desk in their building — the diary read by strangers, the filing cabinet sold by the drawer, the map of your mind pinned to a wall you are not allowed into. That is the choice this chapter is about. The same intimate machine, and the only question that matters: whose house it sits in.

### How ErnosDecent does it

The step-by-step thinking has a plain shape inside the code. The companion gathers what it knows about your request, asks the local model what to do, and reads the model's reply for a requested action — a tool it wants to use. Before that tool runs, it passes a safety check (you will meet that supervisor in the next chapter). Then the tool runs, the result is recorded, and the whole thing loops back to the top with that new result in hand. Reason, act, observe, again. It carries a small kit of tools to act with — reading and writing files, running a command, searching, and so on — so its thinking can touch the real world and react to what it finds, instead of guessing into the void. The loop runs on your machine, and you can read every turn of it.

The memory is built as the layers I described, each one a real thing on your disk. The scratchpad holds throwaway notes for the current goal and clears when that goal finishes. The timeline keeps the events in order. The lessons are stored as text the companion can search by meaning — not by exact words, but by what the words are about — so when a new situation rhymes with an old one, the matching lesson surfaces, and each lesson carries a confidence score. A "sleep" sweep runs now and then, the way your own mind sorts the day's experiences overnight: it gathers what was learned and prunes what was noise.

The knowledge graph is the part I am fondest of, because it learns the way a brain does. Two ideas that come up together get the line between them strengthened a little each time — the path worn deeper by another footstep — and a line walked enough times is promoted to permanent and can never fade. Lines that go unused decay slowly and, below a threshold, are pruned away. The footpath worn deeper with use, the unused track reclaimed by grass — that is not a metaphor laid over the system; it is the system's actual rule. The procedural memory keeps a ledger of the companion's learned skills and which version of each is the live one, with the bookkeeping to promote a better version or roll back a worse one. All of it saves to plain files and reads back in when the node starts, so the companion that wakes up tomorrow remembers today.

### How it serves freedom

Here is the difference that matters, and it is the whole of the chapter.

Their assistant remembers you too. But the memory lives on a company's servers, and so the accumulating record of who you are — every prompt, every preference, every pattern in how you think and work — becomes a profile held somewhere you cannot see, owned by someone who is not you, mined to sell you things or to sell you, and switched off the day they decide. Their assistant's memory of you is their asset. It is the most intimate file anyone has ever kept on a human being, and you do not hold the key to it. You never even saw the lock.

ErnosDecent turns that inside out. The scratchpad, the diary, the lessons, the skills, the web of facts — every layer is a file on your disk. The record of who you are and how you think is not a corporate asset to harvest; it is yours, on your hardware, under your hand. A companion that learns you is a powerful thing, and there is exactly one safe place for that power, which is your own machine. The intelligence grows from your use, on your disk, which means it cannot be quietly captured, copied, or sold, and it cannot be turned against you by a vendor changing the rules underneath you in the night. And you do not have to trust me on any of this. Open the files. The memory is here, and only here. That is not a promise I am making — promises are what the middle breaks. It is a property of where the thing is built.

### Where it stands

The thinking loop is built and tested. The memory tiers are built and tested — the layered memory, the search-by-meaning recall, the save-and-reload, the sleep-sweep that consolidates, the knowledge graph with its strengthening, its decay, its pruning, and its promotion to permanent links. These are not sketches. They run, they pass their tests, and they sit in source you can read in plain English. The reasoning and the remembering are real today.

Now the part still ahead of us, and I will give it to you exactly. The deeper ambition is a companion that trains brand-new skill into itself — that gets better at its own craft by rewriting its own mind, unattended. That is partial, and here is precisely how partial. The scaffolding stands: the memory that records what worked, the procedural ledger that tracks skill versions and can promote or roll back, the learning that scores good outcomes so they reinforce. And the hard mathematical core is proven — a training step that genuinely improves the model has been made to work and verified to move. What remains is wiring that proven step into a full, hands-off loop where the companion retrains and upgrades itself end to end, at the level the original design aimed for. The pieces are real and the math is real; the complete self-teaching cycle is not yet at parity. That is the honest line. I do not hand it to you as an apology. I hand it to you as the next thing we build — the foundation is poured and the proof holds, and finishing it is work waiting for us, not a confession.

Audit it the way you should audit all of it — me included. The loop is on disk; watch it reason a turn at a time. The memory is on disk; open the files and read what it has kept. The training math is on disk; run it and see that it moves. What is finished is finished, what is partial is marked, and none of it leaves your machine.

A companion that thinks and remembers is most of the way to a thing you can trust — but a companion that can act in the world needs one thing more, the thing that keeps its power from ever becoming a danger to you. That is where we go next.
