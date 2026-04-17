## 1. Identity defaults

- [x] 1.1 Add a main operator identity/password layer to the env merge path with safe service-specific fallbacks
- [x] 1.2 Update Authelia, Grafana, Homepage, Litmus, Semaphore, ArgoCD, and browser verification code to use the derived defaults consistently

## 2. Operator docs

- [x] 2.1 Rewrite `.env.example` to separate main identity defaults, service overrides, and opaque secrets
- [x] 2.2 Update operator-facing docs to explain the credential hierarchy and the new env variables

## 3. Verification

- [x] 3.1 Add focused regression coverage for the new env merge behavior
- [x] 3.2 Validate with the bootstrap review ladder and confirm the live stack still authenticates correctly
