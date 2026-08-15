---
title: Docent Reference Demo
emoji: 🧭
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
fullWidth: true
short_description: Bounded Docent with a verified OpenBGI Constitution
---

# Docent reference demo

This Docker Space runs the generic Docent reference implementation in deterministic mode. Its default collection combines the self-docent with a verified, hash-pinned snapshot of the OpenBGI Constitution for Beneficial AGI, Draft 0.6.

No model credential is required for the reference deployment. The browser calls Docent, Docent retrieves bounded public evidence, and deterministic mode returns the best matching source record without pretending that model synthesis occurred.

The canonical Constitution source is independently checked for drift by the GitHub repository; normal Space runtime reads the checked local snapshot and does not fetch Google Docs.

Future mediated inference belongs behind Docent's provider boundary through AlphaClaw rather than in this Space's public client configuration.

See the [canonical GitHub repository](https://github.com/PaulTiffany/docent) for source, tests, provenance locks, deployment instructions, and scope boundaries.
