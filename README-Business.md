# ErnosDecent — Business Edition

**Run your own localised, decentralised infrastructure — identity, storage, messaging, hosting,
AI inference, and media — on hardware you control. Free, self-sovereign, AGPLv3.**

This is the same ErnosDecent engine as [`main`](README.md), with a business-oriented persona and
prompts. It is a *thin overlay*, not a fork of the code — so every fix and feature on `main`
applies here too.

## Why a business would run it

- **Cut cloud bills.** Inference, storage, bandwidth, and identity are served by the decentralised
  mesh instead of metered cloud services.
- **Self-sovereign & private.** Self-hosted; no phone-home. Data and computation stay on
  infrastructure you control; nothing leaves the node without explicit instruction.
- **No vendor lock-in.** Open protocol, AGPLv3, content-addressed storage — your data is portable
  by construction.

## The catch that isn't a catch

The savings come *from* participating in the mesh, not in spite of it. Your node relays, stores,
and validates for the network; in return it draws on the network's shared compute, storage, and
reach. Adoption-for-savings quietly strengthens the commons. You cannot strip the decentralised
core and keep the savings — see [`ANTI_CAPTURE.md`](ANTI_CAPTURE.md) for why that's by design.

## Quick start

```sh
git clone -b business https://github.com/MettaMazza/ErnosDecent.git
cd ErnosDecent
ln -s /path/to/Ernos-Programming-Language/stdlib ./stdlib   # see main README "Build"
bash build.sh
ERNOSDECENT_PASSPHRASE="choose-a-strong-passphrase" ./node
```

The Business edition is selected by `config/edition.json` (`"edition": "business"`), which loads
`config/business/prompts.json` and `config/business/agent_persona.txt`. Set it back to `"default"`
for the standard node. The edition changes **only** prompts/persona/branding — never the mesh
services that make the savings possible.

## Licence

AGPLv3 (see [`LICENSE`](LICENSE)). If you run a modified version as a network service, you must
publish your modifications. Reciprocity keeps the mesh — and your savings — alive.
