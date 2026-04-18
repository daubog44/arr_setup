## Why

The repo-local browser verification is part of the operator contract for the public UI surface, so false positives are a product bug, not test noise.

Live evidence on April 18, 2026 shows:

- `https://seerr.nucleoautogenerativo.it/setup` renders the expected setup UI in a real browser
- `scripts/verify-public-auth.mjs` still fails that route with `App-native route seerr... rendered an error page: Internal Server Error`
- the failure happens because the verifier reads `textContent("body")`, which includes serialized i18n payloads; Seerr ships the literal translation string `pages.internalservererror: "Internal Server Error"` inside the HTML even when the UI is healthy

That gap matters because a healthy app-native route can incorrectly fail the final browser gate and block `task up` closeout for the wrong reason.

## What Changes

- Tighten app-native browser error detection so it evaluates user-visible page text instead of raw serialized payloads.
- Keep route-level failure markers for real error pages, but stop flagging bundled translations or script blobs as runtime failures.
- Add repository tests that lock the verifier onto the intended visible-text path.

## Capabilities

### Modified Capabilities

- `public-ui-surface`

## Impact

- Affected code lives in `scripts/verify-public-auth.mjs` and `tests/test_haac.py`.
- Verification must include OpenSpec validation, unit tests, and a live browser check against the Seerr public route.
- Rollback is trivial: revert the verifier change if it hides a real visible error, then re-run browser verification with captured evidence.
