## Chapter 18 — Live Video, Neighbour to Neighbour

When you call the person you love, your face is taken hostage on the way.

You and the person you are speaking to may be a mile apart, in the same city, under the same sky — and still your faces do not travel between you. They travel up to a company's machines, sit there in a stranger's keeping for a heartbeat, and come back down. The same is true the moment one person stands up to speak to a crowd — a stream, a broadcast, a witness holding up a camera while something happens that someone powerful would rather you not see. The picture does not come from them. It comes from a company that took a copy, and the copy is the leash. The company can listen to your call. It can slow the stream until the crowd drifts off. It can charge for the privilege of being seen. And when someone with power makes the request, it can cut the feed mid-sentence and call it a policy. The middle of your conversation belongs to a corporation, and the corporation does to the middle whatever it likes. Your most human moments — your face, your voice, the thing you risked to show the world — pass through a turnstile owned by people who have never met you and never will.

This chapter takes the middle out. It is about two people stringing a live audio and video link straight between their own machines, with no company holding a copy of their faces — and about a way for popular video to spread across a whole neighbourhood of nodes instead of pouring through one company's pipe, where one hand can squeeze it. Live, moving media is one of the hardest things to do without a man in the middle, so this is also the chapter where I am most exact about how far it has got. The mission burns; the ledger stays honest. Both, in the same breath.

### The plain idea

Here is the whole shape of it, and it comes in two halves.

The first half is the live call: two machines find each other, agree on how to talk, scramble the line so only the two of them can make sense of it, and then send moving pictures and sound straight across, end to end, with nothing in between. No company in the loop. The conversation runs along a line the two of you string between your own houses, and no one else owns an inch of it.

The second half is for when one person speaks and many watch — a broadcast, not a call. There the trick changes. Instead of a thousand people all dragging the same video out of one exhausted source, the video is chopped into small pieces, and every node that already holds a piece hands it to a few neighbours while pulling other pieces from a few others. Popular video spreads sideways, neighbour to neighbour, the way a rumour spreads through a town — fast, and from no single mouth that anyone can stop.

### An everyday picture — the call

Picture two children with a tin-can telephone: two cans and a taut string pulled tight between them. You speak into your can, the string carries it, and it comes out of the other can. There is no third can in the middle. There is no operator listening. There is the line, and the two ends, and nothing else.

A live call on ErnosDecent is that string, with three honest difficulties solved along the way, and each one has a plain name the moment you unwrap it.

The first difficulty: before two devices can talk, they have to agree on *how* — what kind of picture, what kind of sound, how fast, in what shape. Picture two people starting a phone call who, in the first second, settle which language they both speak and how loudly to talk. The technology that does this settling is called **SDP** — and that is the whole of SDP: two devices, in their opening exchange, agreeing how to talk to each other.

The second difficulty: each machine has to know its own address before it can tell the other where to send the picture — and most home machines sit behind a router that hides their real address even from themselves, the way an office worker may not know the building's number on the street. So each side asks a simple helper out on the internet, "from where you sit, what does my address look like?" — and the helper tells it. That asking-and-being-told is called **STUN**: finding your own address from behind a router, so you can hand it to the person you want to reach.

The third difficulty is the one that matters most: the line has to be scrambled, so that even if someone spliced into the string halfway along, all they would catch is noise. ErnosDecent scrambles the call with methods called **DTLS** and **SRTP**, and the only thing you need to hold is what they do — they scramble the call so that only the two ends can hear it. The two devices agree on a secret no one else knows, and from that instant the sound and the picture are locked to that secret. The string is yours. No one listens by standing in the middle, because the middle hears static.

Put the three together and you have the whole browser machinery for direct live calls — the thing that lets two machines hold a video conversation with no company between them. It has a name, **WebRTC**, and now you know what the name is made of: agree how to talk, find your own address, scramble the line. Three plain ideas, and the eavesdropper is locked out of all three.

### An everyday picture — the broadcast

Now the other half, for when one person speaks and a crowd watches.

If a thousand people all turn to one shopkeeper for the same video, the shopkeeper is crushed under the door. So instead, picture the video cut into a long row of short clips, like a film snipped into single frames you can pass from hand to hand. Anyone who has already caught a clip passes it on to a neighbour; meanwhile they are still gathering the next clips from neighbours of their own. No one carries the whole crowd. Everyone carries a little, and the clips ripple outward across the neighbourhood until everyone watching holds the film — and there is no shopkeeper left to crush, because the work was shared the moment it began.

There is a second, quieter cleverness in the cutting. Each short clip is kept at several qualities at once — a crisp version, a rougher smaller one, and sizes between. A watcher on a fast connection grabs the crisp clips; a watcher on a slow one grabs the smaller clips and keeps watching smoothly instead of freezing. The stream bends to fit the connection it finds, clip by clip, with no one touching a setting. This chopping-into-pieces-at-several-qualities is called **adaptive HLS**, and that plain description is the whole of it: small pieces, several sizes, so a slow connection still gets a watchable picture and nobody is shut out for being poor.

### How ErnosDecent does it

The node carries both halves, built from real parts, not sketches of parts.

For the live call it runs **WebRTC**: the SDP agreement, the STUN address-finding, and genuine DTLS-and-SRTP scrambling of the media — not a pretend lock, but real encryption of the actual sound and the actual picture, done through a battle-tested scrambling library the node calls directly. Two nodes set up a direct, encrypted audio and video link, end to end, with no company holding a copy in the middle. Your face goes to the one person you sent it to, and to no one else, ever.

And the sound and the picture have to be squeezed small enough to cross an ordinary home line, because raw video is enormous — far too fat to push down a household connection as it is. Squeezing it is the job of a **codec**, a method that packs media down small for sending and unpacks it whole at the far end. ErnosDecent uses the real ones the rest of the world uses: **Opus** for sound and **VP8** for video, the same codecs that carry serious live media everywhere there is serious live media. When a connection is too poor even for those, it falls back to simpler, rougher squeezing so the link survives rather than dies. The broadcast half runs the adaptive HLS chopping, and underneath it a **peer-to-peer CDN** — a "content delivery network" with no company owning the delivery — which hunts the small pieces of popular video out on the mesh and pulls them from whichever neighbours hold them, using the shared address book and the content store you met in earlier chapters. Your node can be a tiny relay: streaming a few pieces out to a few neighbours while pulling a few others in, so a popular broadcast spreads across the mesh instead of straining one company's servers — and instead of waiting at one company's switch.

One thing is worth a moment, lightly, because it is unusual and because you can check it. Those real codecs — the genuine Opus and VP8 the professionals lean on — are driven straight from ErnosPlain, the plain-English language the whole system is written in, by reaching directly into the underlying C libraries that do the hard mathematics. Plain sentences, calling into the real machinery, producing real compressed audio and video. You do not take that on faith. It is in the source, in readable English, and it makes real media you can play with your own ears and eyes.

### How it serves freedom

See what this dismantles.

To broadcast, you need no platform — so there is no platform to demonetise you, no company that can quietly switch off the money or throttle your reach because an advertiser flinched. To speak live to a crowd, you need no channel a corporation can suspend — so there is no off switch resting in someone else's hand, waiting. To call another person, you need no service that keeps a copy — so there is no copy to subpoena, sell, or scan, no warehouse of your face for anyone to raid. The picture goes straight from you to them, scrambled to the two of you alone, and the broadcast spreads neighbour to neighbour rather than through a chokepoint anyone can throttle. You broadcast and you watch with no platform standing between you to demonetise, censor, or surveil — because the platform is not slow, and it is not polite, and it is not begged into behaving. It is gone.

Live media is where corporate control is usually most physical you can touch it: the expensive servers, the metered bandwidth, the content rules enforced by whoever owns the pipes. Pooling the delivery across the mesh is what makes rich, live, moving media free of those gatekeepers — not cheaper to rent, but no longer rented at all. The camera in your hand stops being a thing they license you to use and becomes, again, a thing you simply hold up to the world. This is what they were never going to hand over willingly, and so we take it back by building it ourselves.

### Where it stands

This works, and I will be exact about the working, because a thing no one owns lives or dies on whether you can check it.

The WebRTC handshake runs — the SDP agreement, the STUN address-finding, the DTLS-and-SRTP scrambling of the media. The real Opus and VP8 codecs run, driven from plain English into the genuine C libraries, with the simpler fallbacks in place for poor connections. The adaptive HLS chopping runs, and the peer-to-peer CDN swarm — your node relaying pieces to neighbours while pulling from others — runs and is tested. These are real, exercised parts of the system: four modules, getting on for two thousand lines, on disk, running.

The one honest piece of unfinished work is shared with the networking chapter and named there too: getting two machines reliably connected through every kind of home router, at the scale a global service runs, leans on heavier address-finding machinery marked for after the first full release. That is not a hedge and it is not an apology — it is the next stretch of road, and it is ours to lay. The link, the scrambling, the codecs, the swarm — those are here, and proven, now.

So check it the way the whole book asks you to. The media is scrambled to the two ends; the picture never sits in a company's machine; the broadcast spreads sideways across the mesh; the real codecs that do the squeezing are right there in readable source, calling the real libraries. Do not trust me that there is no company in the middle of your call. Become the observer. Confirm there is no middle at all.

Sending live video means lending and borrowing a little of each other's connection — strangers carrying a sliver of one another's broadcast so no one carries the whole crowd alone. That lending is the next chapter in full: how your node gives the mesh its strength, and is repaid for it. The string between the two cans was only ever the beginning. The neighbourhood holding it up together is the point.
