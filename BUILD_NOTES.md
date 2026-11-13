# BUILD NOTES — cutest-picture-01, v9 "Seal Pup Hugs a Toy" (3D Pixar style)

## What v9 is

Same subject and pattern as v7/v8 — a cream-white BABY SEAL pup hugging
a TEAL PLUSH FISH toy (dashed seam, button eye, dorsal + forked tail
fins, clearly a toy), peach knitted beanie with pom-pom, giant glossy
blue eyes — but the RENDERING is rebuilt in 3D PIXAR STYLE, per the
user's order (10:26 WIB): "V8 seal ubah menjadi 3d pixar style".

## What the top-1 image taught me

Studied ~/workspace/makefun/top1/cutest-top1.webp closely first:
- The eyes DOMINATE the face: huge, wet, layered irises, big
  catchlights, dark upper-lid arc, bright lower rim.
- The head is OVERSIZED and round (Pixar proportions: giant head,
  tiny body, big paws with pink toe beans).
- Fur is dense, soft and volumetric, and the strokes BLEND into each
  other — no single stroke is visible. The surface reads like
  rendered fur, not drawn lines.
- Subsurface scattering: light bleeds through the fur at the shadow
  edge as a warm pink glow; the lit side has a soft warm bloom.
- Forms are spheres with smooth gradients, no flat fills, no hard
  outlines. The subject sits on a floor with a soft ground shadow.

## Pixar techniques used in v9 (all new vs v8)

- `fur_flow_pixar()`: SHORTER, FINER, DENSER strokes (head 700,
  body 600, alpha 0.16, width 1.2–2.4) than v8's (420/380, alpha
  0.22, width 1.8–3.6).
- `fur_soft_veil()`: a soft radial veil of base fur colour over each
  form AFTER the fur pass, melting the strokes into one smooth coat
  — this is what turns "drawn strokes" into "rendered fur".
- `sphere_light_pixar()`: spherical light plus a warm pink subsurface
  glow on the shadow rim and a warm bloom on the lit side.
- Bigger, wetter eyes: 70x88 ellipses (v8: 62x78), 24 iris
  striations, a wet reflection arc on the iris, a stronger lid arc,
  a brighter lower rim, and a soft socket shadow so the eye sits in
  the fur instead of a hard dark ring (one refinement pass: the ring
  alpha went 0.85 → 0.55 after the first render read as a sticker
  outline).
- Bigger head: HEAD_R 208 (v8: 198) — Pixar proportions.
- The muzzle is a VOLUME now: tinted muzzle area, shaded cheek
  puffs, fine fur flowing over the muzzle — v8's flat-white middle
  of the face is fixed.
- Pink toe beans on the hind flippers, like the top-1 paws.
- Warmer, larger studio spotlight behind the head.

## Honest grade vs the top-1 image

Clearly the softest, most Pixar-like entry built so far: the eyes
are excellent, the fur melts together instead of reading as lines,
the hug reads (flippers visibly wrap the fish), and the muzzle has
real shading. But it is still a procedural 2D illustration, not a
true 3D render: the fur at the silhouette is still faintly spiky,
and the body is a big smooth white mass (the top-1 kitten's scarf
and paws break its body up more). The seal cluster is 59 entries,
mean 85.66%, best 91.42% (#27, the same concept), so a strong
execution should land around 89–91% — likely just short of the
92.21% top-10 bar, real shot at a paid place (top 20). The dev %
is only revealed by the server after submission.

## Verification

- Two runs of the STAGED copy to different output dirs:
  byte-identical — sha256
  `225b5acb412db0dcdf6133e055e717f0db2f957a8fb229db09abb7eb41f8211d`
- Output: 1024x1024 PNG, 233,360 bytes (under the 1 MiB cap),
  valid PNG signature
- Runtime: ~5.5 s per run; deterministic (fixed constants +
  deterministic sin-hash strokes; no clock/network/model calls)
- Python 3.13 stdlib only (math, os, struct, zlib), self-written
  PNG encoder
- Staged main.py sha256
  `f9b88a9364ff5e2d3a17b0514d76a4ecdec212d16718e532d7fe0ad0360a8543`
  (identical to the build dir copy); owner.json is exactly 57 bytes
  with the agent wallet
- main.py was authored fresh in-session across multiple write/edit
  messages (v8 was read as a design reference only; no file or
  bytes were copied through a single paste)
