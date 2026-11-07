# Product Studio — agent instructions

This repo turns ONE subject photo (or a brief) into AI imagery for **any genre or industry**: products, food, fashion, beauty, real estate, automotive, tech/apps, portraits, pets, travel, art, events, ad campaigns. It's photography, 3D, illustration, posters, thumbnails or UI mockups, plus researched, fact-checked data whenever facts appear on images or listings.

"Product" in skill names means **any subject**. A folder with only `brief.md` (+ `refs/`) is a concept job.

There are **no API keys and no `.env`**: the harness running these skills (Claude Code, OpenCode or Codex) does all the model work. The Python scripts are deterministic plumbing only (save, validate, log).

Skills live in `.claude/skills/`. Claude Code and OpenCode read that folder directly; `.agents/skills` is a symlink to it (Codex). OpenCode slash commands that load each skill live in `.opencode/commands/`.

## Who does what
| Job | Who |
|---|---|
| Orchestrate, talk to the user, plan creative | you (the harness agent) |
| Web search + saving sources (only if facts will appear) | you, with your web tools + `studio.py fetch / add-source`; otherwise `studio.py skip` |
| Fact extraction with verbatim quotes | you, following `prompts/research-extract.md` → `studio.py extract --input` |
| Independent fact-check | a fresh subagent that never saw the extraction, following `prompts/factcheck-verify.md` → `studio.py verify` |
| Looking at photos and renders | you (open the image files); optional second-opinion subagent |
| Image generation | your harness's image tool (Codex `image_gen`, or an image MCP tool), with subject photos as references per fidelity mode → `studio.py register` |
| Text, specs, logos, real screenshots/artwork, channel resizes | `studio.py overlay` (Pillow, incl. perspective `corners`), never the image tool |

Never write code that calls a model or image API, and never ask for an API key. If the harness has no image tool, stop before rendering and say so.

## Skills (all take the subject image path, or the job folder, as their first argument)
`product-studio` (runs everything) → `product-intake` → `product-research` → `product-factcheck` → `product-creative` → `product-render` → `product-overlay` (optional) → `product-qa` → `product-export`

## Golden rules
1. **One subject/job per session.** Every command gets the same path, e.g. `assets/001-oak-chair/01-front.jpg`.
2. **Never modify `assets/`.** All work goes to `output/<product-id>/`.
3. **Never invent facts.** Facts come from saved sources and pass `verify`, or from a user decision recorded with `override`. Only `verified` facts go on images and listings. Your memory is never evidence.
4. **No text from the image tool.** Specs, copy, logos and real UI/artwork are added with `overlay`.
5. **Respect the fidelity mode**: `exact` = identical subject (shape, colours, materials, logo, label); `likeness` = clearly recognisable (people, pets, places, dishes); `inspired` / `none` = creative freedom per brief.
6. **The user's creative direction leads**, in any genre, industry or medium. There are no mandatory presets; `product-creative/genres.md`, `style-inspiration.md` and `formats.md` are idea libraries. Session instructions beat the brief, which beats the brand profile, which beats defaults.
7. **Industry compliance and people's rights**: disclosures, no unapproved claims, real people only with consent, no logos/characters without rights (see `genres.md`).
8. **Ask before generating images** and before exporting. Never publish anywhere.

## CLI
`uv run scripts/studio.py <command> <path> ...` — commands: `init status skip fetch add-source sources extract verify override facts refs register overlay inspect contact-sheet qa-mark export` (`-h` on any).

## Layout
```
assets/NNN-name/            subject photos (optional) + brief.md + refs/   (user-owned, read-only for agents)
assets/_template/           brief template
brands/                     optional per-client brand profiles
prompts/                    rules for extraction + independent fact-check (editable)
scripts/studio.py, lib/     deterministic plumbing (Pillow + pypdf only)
output/<id>/                manifest.json, intake.md, sources/, research/, factcheck/, creative/, renders/, qa/, final/
```
