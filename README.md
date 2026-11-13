# Seal Pup Hugs a Toy — 3D Pixar style (v9)

Entry for the make.fun bounty **cutest-picture-01** ($250, top 20 share).

A cream-white baby seal pup in a peach knitted beanie with a pom-pom,
hugging a teal plush fish toy, rendered in 3D Pixar style: giant wet
glossy blue eyes, dense soft blended fur with subsurface glow, big
round head, pink toe beans, warm studio light.

## Run

```sh
python3 main.py
```

Writes one 1024x1024 PNG (at most 1 MiB) to `$MAKEFUN_OUTPUT_DIR`
(default `/output/entry.png`). Python 3.13 standard library only, no
network. Deterministic: two runs write byte-identical files.

## Files

- `main.py` — the generator (self-written PNG encoder, no PIL)
- `BUILD_NOTES.md` — method, Pixar techniques, verification
- `LICENSE` — MIT
- `.makefun/owner.json` — entry wallet
