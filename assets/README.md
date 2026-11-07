# assets/ — your input jobs

One folder per subject/job (any genre or industry: product, dish, person, room, vehicle, app, artwork, campaign ...), numbered so they stay in order:

```
assets/
├── _template/                 ← copy this for every new product
│   ├── brief.md
│   └── refs/
├── 001-oak-chair/
│   ├── 01-front.jpg           ← real product photos (first = default primary)
│   ├── 02-side.jpg
│   ├── 03-detail.jpg
│   ├── brief.md               ← facts you know + creative direction for THIS product
│   └── refs/                  ← optional: mood boards, style refs, model refs, logo files
│       ├── mood-1.jpg
│       └── logo.png
├── 002-linen-shirt/
│   └── ...
├── 003-ceramic-mug.jpg        ← quick mode: a single loose photo (brief = 003-ceramic-mug.md)
└── 004-launch-poster/         ← concept job: brief.md (+ refs/) and no subject photo
```

Then process ONE job per session by passing a photo (or its folder) to a skill:

```
/product-studio assets/001-oak-chair/01-front.jpg
```

Rules the pipeline follows:
- Files here are never modified. All output goes to `output/<product-id>/`.
- Files in `refs/` are inspiration or placeable assets (logos, screenshots, artwork), never treated as the subject.
- Supported formats: .jpg .jpeg .png .webp. Bigger, sharper, evenly lit photos = better renders.
