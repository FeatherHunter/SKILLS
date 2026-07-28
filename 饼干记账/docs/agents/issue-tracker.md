# Issue tracker: Local Markdown

Issues and specs (you may know a spec as a PRD) for this Skill live as markdown files in `.scratch/`.

## Conventions

- One feature per directory: `饼干记账/.scratch/<feature-slug>/`
- The spec is `饼干记账/.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `饼干记账/.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` — never a single combined tickets file
- Triage state is recorded as a `Status:` line near the top of each issue file (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

Create a new file under `饼干记账/.scratch/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `饼干记账/.scratch/<effort>/map.md` — the Notes / Decisions-so-far / Fog body.
- **Child ticket**: `饼干记账/.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `饼干记账/.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.

## Skill-specific notes

- 本 Skill 工作目录即仓库根的子目录，所有 `.scratch/` 路径都以 `饼干记账/` 为前缀
- `饼干记账/scripts/` 中的 Python 脚本与 `.scratch/` 互不引用；issue 文件不是脚本输入