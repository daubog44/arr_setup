## 1. Loop Contract

- [x] 1.1 Align `AGENTS.md`, `README.md`, and repo docs with the official OpenSpec CLI change model and the new Ralph loop contract
- [x] 1.2 Add repo-local loop policy docs for prompt, review, discovery, sidecars, and worklogs
- [x] 1.3 Add repo-local skills and stable OpenSpec role prompts for review, discovery, and subagent usage

## 2. Loop Runner

- [x] 2.1 Implement a cross-platform loop bootstrap script that checks readiness, creates worklogs, renders a dynamic prompt, and launches CodexPotter
- [x] 2.2 Add Task entrypoints for loop check, apply, checked apply, discovery, and dry-run modes
- [x] 2.3 Isolate loop runtime artifacts and update `.gitignore` so generated state stays local

## 3. Self-Improvement and Validation

- [x] 3.1 Bind the loop to active OpenSpec changes and narrow discovery when no active change exists
- [x] 3.2 Require a validation and review ladder for bootstrap-affecting work
- [x] 3.3 Validate the new loop entrypoints and the OpenSpec change itself
