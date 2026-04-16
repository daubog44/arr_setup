## 1. Spec And Docs

- [x] 1.1 Add the delta spec for bootstrap/Git boundary cleanup

## 2. Bootstrap Boundaries

- [x] 2.1 Remove `sync` from the default `preflight` / `task up` happy path
- [x] 2.2 Make `push-changes` fail instead of merging when the local branch is behind or diverged

## 3. Modularization

- [x] 3.1 Move low-level Git state helpers out of `scripts/haac.py` into `scripts/haaclib/`
- [x] 3.2 Keep the Argo root manifests explicitly template-driven and covered by the render path

## 4. Verification

- [x] 4.1 Run static validation (`openspec validate`, `py_compile`, `helm template`, `kubectl kustomize`, `task -n up`)
