## Chapter 16 — Searching a Web No One Owns

Type a question into the box, and a stranger decides what you are allowed to find.

That is the arrangement, and we have all stopped seeing it. More has been written down than any person could read in a thousand lifetimes, and the only door most of us have to any of it is to ask one of two or three companies, in a little white box, and take whatever they choose to hand back. We call that "searching the internet." It is not searching. It is petitioning a private gatekeeper and trusting the order it sorts the world into. The company that owns the box decides which pages rise to the top, which sink past the point where anyone looks, and — this is the quiet part, the part you were never meant to dwell on — it writes down every question you have ever asked it. Every fear you typed at two in the morning. Every illness you looked up before you told a soul. Every doubt, every hope, every search you would die before saying out loud. Your curiosity is its inventory. The pages it shows you are the pages it has its own reasons to show you, and the reasons were never yours.

In the last chapter we settled the question of where your files live — on your own machine, in your own hands. This chapter takes back the other half of knowing: not what you keep, but what you can reach. Because owning your own memory means little if the way to everyone else's memory runs through one company's door. So we are going to take the box back. Not improve it. Not beg it to behave. Take it back — until finding things is a thing your own machine does, in the open, where you can stand over it and watch it work.

### The plain idea

Here is the whole of it before a word of machinery: a search engine is two simple jobs wearing complicated clothes.

The first job is *reading and remembering.* Something has to go out, read the pages, and write down which words appear on which pages — so that later, when you ask for a word, a list is already waiting of every page that used it. The second job is *ordering.* A useful word might sit on ten thousand pages, and ten thousand pages in no particular order is the same as nothing at all. So the pages must be sorted, best first, by some honest rule about which is most likely to be the one you wanted.

Two jobs. A reader that takes notes, and a sorter that decides whose note matters most. Everything else in this chapter is those two jobs, done with care, done on your machine instead of theirs.

### An everyday picture

Think of an old library card catalogue — the long wooden drawers, the worn index cards.

Every time you met a book, you read it and filled out a card: this book uses these words, and it points to these other books. You filed the card under each of its words. Now, when you want everything about beekeeping, you do not re-read the library. You pull the "beekeeping" drawer and there the cards are, waiting. That is the reading-and-remembering job, and the drawer of cards has a plain name in the trade: an **index.** A list that runs from words to the pages that contain them, built once so you never search blind again.

But which beekeeping card goes on top? Here two instincts come in, and you already use both without ever naming them.

The first: a card crowded with "bee, hive, honey, beekeeping" is more about beekeeping than one that mentions a bee once in passing. The more your word is genuinely *about* the page, the higher it earns its place. But you also know to discount the words everyone uses — "the," "and," "is." No page is about "the." So the rare, telling words count for everything and the common ones count for almost nothing. That balance — how well a page's words match what you asked, with the everyday words weighed down to near silence — has a name only because engineers needed one to write it down. It is called **BM25.** You do not need the name. You need the instinct, and the instinct is already yours: a page earns the top by how much it is truly about your question, judged on the words that actually set it apart.

The second instinct is about trust, and it is older than any catalogue. When you want to know which book on a subject is the good one, you do not count how loudly it praises itself. You look at who points to it. A book the best books all cite is likely a book worth your time. And it runs deeper: a word from someone everyone trusts counts for more than a word from a stranger. One careful expert pointing to a page tells you more than a thousand idle mentions. That instinct — a page is trusted the more *trusted* pages link to it — is the second rule, and its name is **PageRank.** It never asks a page how important it is. It asks the rest of the web, and it listens hardest to the voices the web itself listens to.

Put the two together and you have the whole sorter. BM25 asks, *is this page about what you said?* PageRank asks, *and does the wider web trust it?* Best of both, top of the list. No one in a boardroom touches the ordering. The rule does the work, in the open, the same for everyone.

### How ErnosDecent does it

In ErnosDecent both jobs run on your own node, and you can read every line of how.

A **crawler** does the reading. It visits pages, pulls out the words, notes which other pages each one links to, and writes it all into an index that lives on your machine — a list running from each word to every page that used it. That index is your card catalogue, built by you, kept by you, answering to you. No trip to a company's servers. No log of your questions stored in someone else's building. The drawer of cards sits in your own house, where it belongs.

When you ask something, the node scores the matching pages with both rules. It runs **BM25** to measure how well each page's words fit your question, weighing down the common words so they cannot drown the telling ones. It runs **PageRank** to measure how much the rest of the web trusts each page — worked out by letting trust flow along the links, over and over, until the scores settle: a page lent weight by the weighty pages pointing to it, which were themselves lent weight by the pages pointing to *them.* And here is a small, honest detail, told because you should be able to catch us on it: the maths inside BM25 normally leans on a curve that wants decimal numbers, and our language prefers whole-number arithmetic, so we do that one piece in fixed steps of whole numbers instead. It reaches the same ranking by a slightly more careful road. The road is on disk. You can read it.

Then comes the piece that makes this a *network's* search and not merely yours: **merging.** Your node holds the slice of the web it has read. Your neighbour's node holds a different slice. So when you search, the results from your index and the results from your peers' indexes are pooled into one list, scored on the same rules, and handed back as a single answer. The search is spread across the mesh — many small catalogues, pooled in the open — instead of locked in one company's vault. No single index. No single ranker. No one owner of what can be found. This is the same shape as everything in this book: not a better king of search, but no throne for a king to sit on.

### How it serves freedom

Whoever orders the answers owns the question.

Sit with that, because it is the whole fight in one line. A company that ranks the world's knowledge never has to ban a page to bury it. It only has to drop the page to the eleventh screen, where no eye ever lands, and the page may as well not exist. It never has to forbid an idea. It only has to rank a paying answer above a true one, and most of us take the first thing offered and never know what we were steered past. And all the while it is copying down what you wanted to know — building a portrait of your mind that you never agreed to sit for, that you cannot see, that it can sell, hand to a government, or use to move you. Control of search is control of attention, control of what you buy, and a standing confession of every private thing you ever wondered. That power has been gathered, quietly, into a handful of firms — and the names on those firms are not the point. The names changed before and will change again. The mechanism did not: one middle, ordering the world, charging the toll, keeping the list.

A search that runs on your own machine, over an index you can read, scored by rules you can check, pooled across a mesh no one owns, tears that lever out of every single hand. There is no top to capture. No firm can rank the world for profit, and no firm can bury what it dislikes, because there is no firm — there is your catalogue and your neighbour's, pooled in daylight, ranked by a rule anyone can audit. And no one keeps a list of what you asked, because the asking happens at home, where the asking always belonged. This is not a promise that a kinder company will behave. It is a property of how the thing is built, true even when no one is trustworthy — which is the only kind of freedom that was ever real.

### Where it stands

Be plain about this, because plainness is the whole point and the whole proof. The crawler works. BM25 works. PageRank works. The merge that pools your results with your peers' works, and every one of these is driven by tests written into source you can open and read in ordinary words. It is real. It runs.

It is also early, and I will not dress it as more. What stands today is a working skeleton of decentralized search — the reader, the two ranking rules, the pooling — proven in the small. It is not yet a web-scale engine crawling billions of pages, and I am not going to paint it as one. But hear where that leaves us, and hear it as a call and not a confession: the hard part is done. The load-bearing idea — that finding things need not pass through one gatekeeper, that an index and an honest ranker can live on ordinary machines and be pooled across a mesh — is built, and it is demonstrated, and you can run it this afternoon. Growing it to web scale is engineering. It is hours and machines and many hands. It is not invention, and it is not waiting on anyone's permission. This is exactly the kind of work that no single person should do and no single company should be allowed to — which means it is ours. So: audit it. Read the crawler. Read the two scores. Watch results from two nodes come back as one list, and confirm with your own eyes that no company stands between your question and its answer. Then help us crawl the rest.

You can find things now without asking permission. That closes Part Four — the part where your machine learned to carry, to store, and to seek for you, owing no one. The next chapter turns the last corner of it: from reaching what others have published to publishing yourself. In Chapter 17, you stop renting a place to speak and become your own website and your own post office — no platform, no landlord, no one who can take the microphone away. The web stops being a place you visit and becomes a place you are.

The work is on disk. It runs. Audit it — and wake up.
