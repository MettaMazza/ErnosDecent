# Part Four — Remembering: Storage, Names, and Finding Things

## Chapter 14 — Keeping Things, Together

Your memory is not in your house.

The last chapters handed you a name no one issued, money no one can freeze, a voice no platform can silence. Now hold up the thing all of that is made of — the record of your life — and look at where it lives. Not with you. Your photographs are on a company's servers. Your documents are on a company's servers. The things you wrote, the places you went, the faces of the people you have lost — all of it sits on machines you have never seen, owned by people you will never meet, who can read it, lose it, raise the price on it, or delete it on a Tuesday afternoon and send you an email about it on Wednesday. You call it "the cloud," which is a soft word for someone else's computer. You are renting the right to remember your own life, and the rent goes up, and the landlord keeps a key.

Sit with that. Your past is held hostage by a stranger who has already decided you are the product. Every memory you keep is one they could take. That is not storage. That is a leash, and it was tied while you were told it was a gift.

This chapter is about cutting it. It is about keeping things — your files, your shared lists, the work two people do together — in a way where no company holds them, no company can quietly change them, and two copies edited apart still come back together on their own, with no boss in the middle to decide who was right.

### The plain idea

There are two ideas here, and both are simpler than they sound once the words come off.

The first is this: a file should be named by what is inside it. Not by a label someone slapped on the outside — not "report_final_v2_REALLY_final.doc," not a row number in a company's database — but by the contents themselves, boiled down to a short, unique fingerprint. Give the file to a machine; the machine reads every byte and produces a fingerprint. Same bytes, same fingerprint, every time, on any machine, forever. Change a single comma and the fingerprint changes completely. The name *is* the contents. And a name that is the contents cannot lie about what it holds — not to you, not to anyone, not ever.

The second is harder and stranger and is the real fire of this chapter: two people can hold the same shared thing — a list, a note, a document — and both edit it at the same time, on different machines, with no internet between them, and when they finally meet, the two versions merge into one. Not "one wins and the other is lost." Not "a server decides." They combine, cleanly, and both machines arrive at the exact same answer without ever asking anyone's permission. No referee. No tie-breaker in a head office. Just arithmetic that cannot disagree with itself.

Hold those two together, because together they take something away from the people in the middle: the power to keep your memory, and the power to be the boss of it.

### An everyday picture

Start with the first idea, the fingerprint.

Picture a library where the books are not shelved by call number. They are shelved by a fingerprint taken from the exact words inside each one. Ask for that fingerprint and you are handed *that book* — precisely that one, not a near-copy, not a tampered reprint. And here is the quiet power of it: if someone slipped into the library at night and changed one sentence in one book, that book would no longer match its fingerprint. It would be a different book on the wrong shelf, and the mismatch would scream. You would not have to trust the librarian. You would not have to remember the original sentence. The shelf itself would tell you something had been touched.

That is what it means to name a file by its contents. Two people who save the identical photo end up with the identical fingerprint, so the network stores it once instead of twice — they were the same file all along, and the naming made that plain. And nothing can be altered behind your back, because altering it changes its name, and the old name no longer points to it. Think about how much of the world's power is exactly this: the power to change the record and swear it never changed. This takes that power away from everyone, including the ones who count on it most.

Now the second idea, the one that sounds impossible.

You and a friend keep a shared shopping list. You are on a train with no signal; your friend is at home. You add "bread" and "apples." Your friend, at the same moment, adds "milk" and crosses off "eggs." Two copies of the same list, edited apart, neither of you knowing what the other did. In the old world this is a disaster — somebody's changes get clobbered, or a little box pops up demanding you choose which version to keep and throw the other away. In this world, your train pulls into the station, the two phones see each other, and the list simply becomes correct: bread, apples, milk, eggs gone. Both additions kept. The deletion honoured. No question asked, because the rules of how a list merges were settled in advance, in the maths, so that any two copies always land on the same final answer no matter what order things happened in.

That is the trick. The list does not need a boss because the list cannot disagree with itself. And once you have seen that, you cannot unsee what every server in the middle was ever for: it was the boss you did not need.

### How ErnosDecent does it

The node holds your files in what is called **content-addressed storage** — storage where the address of a thing is a fingerprint of the thing.

It works the way the library does. When you store a file, the node breaks it into chunks and runs each chunk through a fingerprinting machine — a **hash function**, which takes any amount of data and crushes it down to one short, fixed string that acts as that data's unique name. ErnosDecent uses **SHA-256**; you do not need the name, only what it does: identical data always gives an identical fingerprint, and the smallest change gives a wildly different one. Identical chunks are stored once. Tampering is caught the instant a chunk no longer matches its name. The file's name is computed from the file, by you, on your machine — not handed down by anyone.

For two machines to keep large stores of these chunks in step, the node uses a **Merkle tree** — and the plain way to hold it is *fingerprints of fingerprints.* You take a pile of chunk-fingerprints and fingerprint them together into one fingerprint above. Then you do it again, and again, until the whole store rolls up into a single fingerprint at the top. Now two machines can compare their entire libraries by comparing one number. If the top numbers match, every chunk beneath is identical and there is nothing to discuss. If they differ, the two machines walk down the tree together — left or right, which branch disagrees? — and in a few steps they have pinpointed the exact chunk that differs, without dragging the whole library across the wire. Fingerprints of fingerprints, so two machines can find precisely what is different and trade only that, between themselves, with no warehouse in the middle holding the master copy.

For the living, shared, edited-together kind of data — the shopping list, the shared note, the running count — the node uses something with a forbidding name and a friendly job: a **CRDT**, a "conflict-free replicated data type." Read it backwards. *Replicated:* every machine keeps its own full copy. *Conflict-free:* the copies are built so they cannot end up in a fight that needs a referee. The merge rules live inside the data itself. ErnosDecent ships several of these building blocks: a counter that everyone can add to and that always totals the same; a set where, when one person adds an item and another removes it at the same instant, a clear rule decides the outcome the same way on every machine; a register that holds a single value and keeps the newest by an agreed clock. Stack those small pieces and you get shopping lists, shared documents, collaborative anything — all of which two people can edit offline, in two places, and reconcile to one identical result with nobody in the middle.

No server settles the argument because the maths guarantees there is no argument to settle.

### How it serves freedom

Look at what this removes.

It removes the landlord. If your files are named by their own contents and stored on machines you choose, no provider holds them hostage, no provider scans them, no provider vanishes them when the company is sold or the terms change or your face stops fitting. Your memories stay with you. They sync between your phone and your laptop and your friend's machine, but they are never *handed over* — never sold, never indexed for advertising, never quietly mined while you sleep.

It removes the silent edit. Because every file's name is a fingerprint of its contents, nothing can be changed without changing its name, and the change is visible to anyone who checks. There is no version of this where a record is altered and you are told nothing. The library shelf screams. Remember what that power is and who has always held it: the power to rewrite what happened and dare you to prove otherwise. Whole regimes are built on it. Content addressing takes it off the table — not by asking the powerful to be honest, but by making the record refuse to lie.

And it removes the referee. The reason two people normally need a central server to work together is to settle conflicts — to be the boss who decides whose change wins. The conflict-free data types dissolve that need. Two people, or two hundred, can keep a shared thing in step with no company sitting in the middle taking a cut and reading the contents on the way through. Collaboration without a coordinator is collaboration no one can switch off.

Your memory comes home. It stays yours. It stays unalterable behind your back. It stays shareable without a master. Three locks taken off your own past at once.

### Where it stands

This is built, and it works, and it is tested. I will not soften that and I will not inflate it.

The content-addressed store is real: data is chunked and named by SHA-256 fingerprints, deduplicated, and verified. The Merkle trees are real, doing the fingerprints-of-fingerprints work that lets two machines find their differences fast. The conflict-free data types are real — the counters, the sets, the registers with their built-in merge rules — and they reconcile to the same answer the way they are meant to. It is five modules and roughly two and a half thousand lines, exercised by their own test suites, in source you can read in plain language. This part of taking your memory back is not a plan. It is on disk, and it runs.

Check it the way you should check all of it — trusting me least of all. Save the same file twice and watch one copy stored. Change one byte and watch the name change. Edit a shared list in two places at once, bring the copies together, and watch them merge to the same result with no server consulted. You do not have to believe me that nothing is altered behind your back. You can confirm, with your own hands, that a thing's name is its contents, and that a name like that cannot lie. That is the whole point of a thing no one owns: anyone can tear it open and see.

Your memory is yours again. But it is still wearing those long cryptographic strings for names — and a name you cannot remember is a name you cannot use, a fingerprint is no good for calling a friend. So the next chapter gives you a human one: names that can't be repossessed.
