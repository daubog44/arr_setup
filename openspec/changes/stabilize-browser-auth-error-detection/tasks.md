## 1. Verifier contract

- [x] 1.1 Update app-native browser verification to detect generic error pages from visible body text only
- [x] 1.2 Preserve selector-based success checks so healthy routes still prove the intended UI rendered

## 2. Validation

- [x] 2.1 Add repository coverage that locks the verifier away from raw `textContent("body")` for app-native route errors
- [x] 2.2 Validate with OpenSpec, unit tests, and a live browser check against Seerr
