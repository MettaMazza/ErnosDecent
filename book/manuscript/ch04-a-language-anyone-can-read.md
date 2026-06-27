## Chapter 4 — A Language Anyone Can Read

The last chapter ended on three laws an exit must obey: owned by no one, readable by anyone, running on your own machine. This chapter is about the second law, and about the quiet trick that has kept it broken for as long as software has existed. Because *readable by anyone* sounds like a courtesy. It is not. It is a battle line, and almost everyone has been standing on the wrong side of it without being told there was a side at all.

Start with what software actually is, stripped of mystique. It is instructions — a long, exact list of steps a machine carries out, one after another, with no judgment and no mercy. That is all. The programs that decide whether your loan is approved, whether your post is seen, whether your account still exists tomorrow — every one of them is a list of steps someone wrote down. And in principle, anyone could read that list and see, in the open, exactly what is being done to them.

In practice, almost no one can. Not because the steps are hidden — a great deal of software is published for all to see — but because of how the steps are written. They look like this:

```
int factorial(int n) {
    if (n < 2) return 1;
    return n * factorial(n - 1);
}
```

You do not need to understand that, and the fact that you do not is the entire point. Even when the instructions are out in the open, they are written in a dense weave of symbols, brackets, semicolons, and clipped abbreviations that you must be trained — usually formally, usually expensively — to read. So the recipe is public and the recipe is a locked box. *Allowed* to read it and *able* to read it are two different freedoms, and the second one was quietly taken from you.

Look at what that wall is, and where you have seen it before. It is the fourth mask from the last chapter — the academic control, the one that decides who is permitted to know — rebuilt one floor down, inside the very tools that were sold to us as the great equalizer. A system that calls itself open while its openness can be used only by a credentialled few has not torn down the gate. It has moved the gate somewhere you were less likely to look, and then told you the door was always unlocked. The names changed. The mechanism did not.

So a real exit cannot be written in the locked language. It would carry the lock inside it. The exit has to be written in a language anyone can read. That language is called Ernos, and it is the second foundation this whole system stands on.

### What it looks like

Here is the same program — multiply a number down to one, the thing called a "factorial" — written in Ernos:

```
define factorial with n as Int returning Int:
    if n < 2:
        return 1
    return n * factorial(n - 1)
```

Read it aloud. *Define factorial, with n as a whole number, returning a whole number. If n is less than two, return one. Otherwise, return n times factorial of n minus one.* That is not a translation I am handing you to be kind. There is nothing to translate. The code *is* the plain-English sentence. What it says and what it does are the same thing, and you just read both.

There are no curly braces. No semicolons. No clipped stand-ins for ordinary words. You say `define` to make a new instruction, `set x to 42` to give something a value, `display` to show something, `for each item in list` to act on every item, `repeat while` to keep going until something changes. Conditions are written the way you would speak them — `equals`, `is not equal to`, `and also`, `or else`. The shape of the program is set by plain indentation, the way you indent a sub-point in a list, instead of by a hedge of punctuation grown specifically to keep you out.

It reads like instructions to a person because that is exactly what it is: instructions a person can read.

### Why this is not a small thing

It is tempting to file this under *nice touch* — a friendlier coat of paint on the same old machinery. Refuse that. It is not paint. It goes to the marrow of everything this book is for.

A programming language is power. Plainly: it is the power to make a machine do things, and machines now do almost everything that is done to you. For the whole history of that power it has been kept behind a wall of symbols you had to be admitted past — by a university, a company, a course, a credential, an institution that decided whether you were the kind of person allowed near the controls. And the wall did not merely stop people from *writing* software. It stopped them from *reading* it — from checking, with their own eyes, what the systems ruling their days actually do. You were handed a world run by code and forbidden, in practice, from reading the code. You were asked to trust the priesthood because you were never taught the scripture.

A language you can read aloud takes a hammer to that wall. It says, in the plainest words there are: you do not need a degree, and you do not need anyone's leave, to instruct a machine — or to understand one that is being used on you. This is the same move as every other move in this book, carried to the deepest floor. Truth anyone can check. Knowledge with no gate in front of it. Capability put back into ordinary hands. We talk about decentralizing money and messages and servers. This decentralizes the *power to build and to verify* — and that one sits under all the others, because every freedom in these pages is written in code, and a freedom written in a language you cannot read is a freedom you must take on faith. We are done taking freedom on faith.

And it matters who built it, in exactly one respect — never as a throne, only as proof. The person who made this language had no formal training in writing software and no institution at her back. She built the tool she needed to get over the wall, because every existing tool was a wall, and then she built an entire decentralized internet with it. Take that as the demonstration, not as a leader: if the wall can be crossed from the outside, by someone the gatekeepers never admitted, in a language she had to invent because the standing ones were locked, then the lock was never necessary. It was a choice. The gate was always optional. Someone only had to walk through it once in plain sight — and the point is not that she did, the point is that now so can you.

### Plain to read, real underneath

Now the honest engineering, because a thing that reads beautifully and cannot run is a toy, and this is not a toy.

When you write Ernos you are not writing a make-believe language that some slow interpreter limps through. Your plain-English instructions are *compiled* — translated, automatically, into the low-level language the machine runs directly — and the result runs at full native speed, the same speed as the dense, symbol-choked languages it replaces. You write the sentence; the machine runs the metal. You surrender nothing in performance for the plainness. The old trade — that you must accept ugliness to earn speed — turns out to be false, and it was always false. It was the wall defending itself, dressed up as a law of nature. The plainness is free.

There is one more fact, and engineers will know it as the real milestone, so I will say it in plain terms because everyone deserves to understand the milestone too. **The language is written in itself.** The program that translates Ernos into something a machine can run is, itself, largely written *in Ernos* — thousands of lines of it. A language that can describe its own translator has crossed the line from a hobby into a standing thing; it no longer leans on anyone else's tools to keep existing. That line has been crossed here. The plain-English language is plain enough for a beginner to read aloud and serious enough to build itself.

It is young. There is finishing work still ahead of it, and I would far rather you know that than be handed a flawless thing that does not exist — the flawless thing is what the masks sell, and it is always a lie. But hear how I say it, because the saying is the whole stance: *young* does not mean unfinished apology. It means there is more here for us to build, together, in the open, and the door is standing wide for anyone who wants to lift a tool. The headline is true and it is checkable: a real, natively-compiling, largely self-hosting language that reads like plain English — and the entire system this book describes, every part you are about to meet, is written in it. You could open any file of ErnosDecent and read, in something close to English, exactly what it does. That is not a promise. Promises are what the middle breaks. It is the second law, made real and put on disk.

### The foundation under everything

Step back and see the shape. There is a view of the world underneath all of this — that truth and the means to live should be things anyone can check and hold, owned by no one. There is a language that puts the act of building and checking into the plain reach of ordinary people. And there is the system built with that language, which is the rest of this book. Worldview, tool, work — and the tool is the hinge between the other two, the thing that turns *anyone can verify* from a wish into a power you can actually pick up and use.

So when, in the chapters ahead, I tell you that you can audit this system — that you do not have to take my word for one line of it, and you should not, mine least of all — I am not speaking loosely. I mean you can open it and read it, in plain English, and see for yourself. The language is what makes that sentence true instead of comforting. This is the difference between a movement that asks you to believe and a movement that hands you the keys and dares you to check: we hand you the keys. Trust no one in the middle, including the woman who wrote this. Read it yourself.

Two chapters of ground remain. The next goes all the way down to the root — the single idea about reality that everything here, this language included, grows from, and the proof that the method behind it produces results anyone can check, answering to the record and to you and to no institution. The one after draws the whole machine in a single picture — a node, a mesh, a daemon — so that when we open it up and walk it part by part, you already see how the pieces fit.

The wall was never necessary. Here is the proof, written in a language you can read. Open a file. Read a line. Then wake up, and build the rest with us.
