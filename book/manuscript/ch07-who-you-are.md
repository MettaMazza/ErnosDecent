# Part Two — You: Identity and Money

## Chapter 7 — Who You Are, with No One's Permission

Ask the plainest question there is, and watch how strange the true answer turns out to be: on the
internet, who says you are you?

A company does. You "are" an email address a company issued and can close. You "are" a phone number a
carrier rents you by the month. You "are" an account — on a platform, in a bank, behind a government
portal — and every one of those accounts exists for one reason and no other: somewhere, some
organisation typed your name into a row in its database, and it keeps, forever, the power to delete that
row. Read that again, because it is the whole cage in a single sentence. Your name online is not
something you *have.* It is something you are *granted* — handed down to you, fresh each morning, by
institutions that can take it back any hour of any day, for any reason or none, with no warning and no
appeal. This is not rare and it is not a malfunction. People are locked out of their own lives this way
every single day — their letters, their savings, their photographs, their decade of work, their entire
recorded existence sealed behind one account, gone the instant a stranger in a building you will never
enter clicks a button you will never see. You did not do anything. You simply stopped counting.

That is the thing this chapter ends. And it is the right door to open first, because identity is the
root the whole machine grows from. Everything that comes after — your money, your messages, your files,
your published words, your thinking machine — is anchored to one fact: *who you are.* So if who you are
belongs to a company, then everything tied to it belongs to that company too, no matter what they let
you call it. You cannot own your money if you do not own your name. We pull this root up first because
nothing else stands until it is free.

### The plain idea

Here is the whole of it, and it is genuinely simple the moment the words are taken apart: your identity
is a pair of very long secret numbers your own computer makes — for you, out of nothing, in an
instant — that nobody hands you, nobody records, and nobody can take away.

They are called **keys.** They come in twos, and the two work together as a matched pair. One key is
**public.** You can give it to the whole world, paint it on a wall, shout it down the street — it is
your name on the network, and it is meant to be seen. The other key is **secret.** You never share it.
It never leaves your machine. It is the living proof that you are the one the public key names. And the
mathematics that binds the two has a property so clean it feels like a trick: holding the secret key
lets you do things that anyone, using only your public key, can *check* — but can never *fake.* You
prove you are you without ever once showing the thing that proves it. You keep the proof and give away
only the verdict.

There is no registration. No server. No sign-up. No password-reset desk — because there is no one to
reset anything with, and nothing of yours sits on their side of a counter waiting to be reset. Your
computer makes the keys, and from that instant you have a name that is yours by mathematical fact. Not
by leave. Not on loan. By fact.

### An everyday picture

Think of a wax seal and a signet ring.

In an older world, an important letter was closed with a blob of hot wax, and the sender pressed a ring
down into it, leaving a mark no other ring could leave. Anyone who received the letter could look at the
seal and know it at once — *that is the mark of the one who sent this.* But only the person holding the
ring could ever make that mark. The seal was public: everyone had seen it, everyone could recognise it.
The ring was private: one person on earth held it, and that was the whole point.

Your keys are exactly the seal and the ring. Your public key is the seal the world can recognise. Your
secret key is the ring, and only your hand holds it. When you "sign" something — a message, a payment, a
post, a single word — you are pressing your ring into the wax: anyone alive can confirm the mark is
yours, and no one alive can forge it. But here is the difference from the old world, and it is the
difference that breaks the cage: in the old world a king or a guild or a lord handed you the ring, and
what they handed they could seize. Here, no one hands you anything. Your machine cuts the ring. The ring
is yours from the first second. And no authority on this earth can confiscate a thing it never gave you,
never touched, and does not hold.

### How ErnosDecent does it

The node makes you not one pair of keys but two, because being someone has two jobs.

The first pair is for **signing** — for stamping a thing as truly from you. ErnosDecent uses a
well-worn, heavily tested method called **Ed25519** for this. You never need the name again; you need
only what it does: it lets you press your seal, and lets anyone on earth check that seal, and lets no
one counterfeit it. The second pair is for **encryption** — for sealing a message shut so that only the
one person it is meant for can open it; that pair uses a companion method called **X25519.** Hold the
two apart in your mind, because they answer two different questions. Signing proves *who said it.*
Encryption decides *who can read it.* You will meet encryption properly in the chapter on private
messages. For now, carry one thing forward: your identity is born holding both powers at once, the power
to be known and the power to keep a secret, and it holds them from its first breath.

Your public signing key is then wrapped into something with a grand-sounding name and a dead-simple
purpose: a **DID,** a "Decentralized Identifier." It looks like a long ribbon of characters —
`did:key:z6Mk…` — and everything that matters about it is hiding in the middle word: *decentralized.* It
is a name that carries its own proof inside itself. Anyone who receives your DID can verify, alone, on
their own machine, with the power off and the network cut, that a message signed by you truly came from
you — without phoning a central registry, because there is no central registry to phone, and never will
be. Sit with how strange and how total that is. Today your name is a lookup in someone else's records,
and whoever owns the records owns the answer. Here your name *is* the answer. It is a self-contained
mathematical fact that travels with you and needs no one's filing cabinet to be true. That is what lets
a name work in a world with no master list: it stopped being a permission and became a property of the
universe.

Your secret keys are the crown jewels, so the node guards them as such. They live in an encrypted
**keystore** — a locked file on your own disk — sealed shut with a passphrase only you choose and only
you know. And because a short passphrase could be guessed by a machine grinding through millions of
tries a second, the node deliberately drags your passphrase through many thousands of rounds of
scrambling before it becomes the key to the store, so that every single guess an attacker makes costs
them real, burning time. The keys never leave your machine. Not to a company. Not to the network. Not to
me. There is no copy in a cloud, no escrow, no spare set held "for your safety" by someone who has
appointed themselves your guardian. There is your ring, in your hand, behind your lock, and that is all
there is.

One more piece, because you may already be turning over the obvious objection. If there is no central
authority, who decides what you are *allowed* to do — which actions are yours to take, which doors are
yours to open? The answer is a clean inversion, and it has a name: **capability authority.** Instead of
every action stopping to ask a central guard "is this person on the approved list?", you simply *hold* a
signed permission — a small token, stamped with the right seal, that says, in effect, "whoever holds
this may do this one specific thing." It is the difference between a guest list and a ticket. A guest
list needs a doorman, and a master roll, and a single point where someone decides who is in and who is
out — which is to say, it needs a middle, and the middle is the whole disease. A ticket needs none of
that. It carries its own permission in its own face. You show it, anyone can read the stamp, and no
central list is ever consulted because none exists to consult. Your keys let you do both halves: issue
such tickets to others, and prove the ones you have been handed. Authority stops being a place and
becomes a thing you hold.

### How it serves freedom

Now stand back and look at what has actually happened here, because this one piece is the hinge the
entire mission turns on, and if you feel nothing else in this book, feel this.

If no company, no university, no bank, no government, and no church *grants* you your identity — then
not one of them can *revoke* it. Follow that all the way down and refuse to look away from where it
leads. There is no account to suspend. There is no row in a database to delete. There is no doorman to
bribe, no servant of the state to pressure, no court order that can reach into a registry and strike you
from the record — because there is no registry, no record, no door. There is a seal that is yours and a
ring that no other hand on earth can hold. You stop existing on the internet by permission. You begin
existing by cryptographic fact. And here is the part the masks have spent four hundred years praying you
would never work out: every kind of control named in Chapter Two — the money, the governments, the
institutions, the experts — every one of them rests, in the end, on a single power, the power to decide
*who counts.* That is the lever under all of it. This takes that lever out of all of their hands at
once, at the root, and lays it in yours. Not softens it. Not regulates it. Removes it.

This is also exactly why it had to come first. Every other freedom in this book is built directly on top
of this one. Your money, in the very next chapter, is value that only your keys can move. Your messages
are letters only your keys can seal and only the reader's keys can open. Your published words are posts
only your keys can sign. Pull identity out of the companies' hands, and everything tethered to it comes
loose and comes home with it. Leave it in their hands, and nothing else you build can ever truly be
yours. This is the load-bearing wall. We set it true, and the house can stand.

### Where it stands

This part is real, and it works. Say that plainly and say it with conviction, because here the fire and
the honesty are the same thing. The node generates your signing keys and your encryption keys. It builds
your self-verifying DID. It locks your secrets inside the encrypted keystore, behind the slow,
hardened passphrase. It issues and checks capability tokens. And none of this is a claim you are asked
to swallow — it is exercised by its own tests, written into source you can open and read this afternoon
in plain English. It is roughly two and a half thousand lines of the system, and it is the most
load-bearing stretch of code there is, because every other freedom in the book hangs its full weight
from it.

So check it the way you should check every word I tell you — by becoming the observer, not the believer.
The keys are made on your machine; watch them be made. The secret never leaves; confirm it never leaves.
The proof that a thing is "yours" is a piece of mathematics anyone can verify and no one can
counterfeit; verify it yourself, with your own eyes, on your own hardware. You do not have to trust me
that no company holds your identity. Do better than trust me. Prove there is no company in the loop at
all, and then you will never again have to take anyone's word for who you are.

You are you, now, by your own hand — not granted, not on loan, not revocable, not for sale. The next
chapter gives that self-owned name the first thing worth holding: money that answers to your keys, and
to no bank on this earth.
