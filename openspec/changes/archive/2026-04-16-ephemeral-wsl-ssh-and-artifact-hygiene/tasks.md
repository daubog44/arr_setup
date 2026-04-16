## 1. Spec And Docs

- [x] 1.1 Add the delta spec for ephemeral WSL SSH runtime and operator artifact hygiene
- [x] 1.2 Update `AGENTS.md` so temporary operator artifacts must live under `.tmp/`

## 2. WSL Runtime Hygiene

- [x] 2.1 Keep the WSL SSH key and `known_hosts` copies in a per-run runtime directory under `.tmp/`
- [x] 2.2 Ensure the runtime directory is cleaned up after the Ansible run while syncing `known_hosts` back

## 3. Repo Artifact Hygiene

- [x] 3.1 Remove stray operator-created investigation artifacts outside `.tmp/`
- [x] 3.2 Add an explicit cleanup command for known stray local artifacts created during investigation

## 4. Verification

- [x] 4.1 Run static validation (`openspec validate`, `py_compile`, `doctor`, `task -n up`)
