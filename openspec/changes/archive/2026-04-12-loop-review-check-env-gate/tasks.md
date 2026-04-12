## 1. Review Contract Alignment

- [x] 1.1 Update `docs/loop-review.md` and `.codex/skills/haac-loop-review/SKILL.md` so bootstrap-affecting rounds run `python scripts/haac.py check-env` as an explicit gate before `doctor`, dry-run, or live `task up`
- [x] 1.2 Update `docs/haac-loop-prompt.md` and `docs/loop-worklog.md` so blocker reporting distinguishes `check-env` failures from toolchain-only `doctor` results

## 2. Validation

- [x] 2.1 Validate the new change with `openspec validate loop-review-check-env-gate` and a targeted grep/readback confirming the updated ladder and worklog language
