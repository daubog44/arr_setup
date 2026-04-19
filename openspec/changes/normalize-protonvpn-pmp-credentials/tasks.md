## 1. Credential normalization

- [x] 1.1 Normalize the repo-managed ProtonVPN OpenVPN username so the forwarding suffix ends in `+pmp`
- [x] 1.2 Document the raw-input versus generated-secret contract in `.env.example` and `README.md`

## 2. Validation

- [x] 2.1 Add focused unit coverage for the ProtonVPN username normalizer
- [x] 2.2 Validate with OpenSpec plus a live `task up` and `media:post-install` rerun after the secret rotates
