## Design

### Inputs

- Existing Seerr admin session established through `seerr_login_with_jellyfin(...)`
- Existing public domain contract from `DOMAIN_NAME`
- Seerr admin API routes:
  - `GET /api/v1/settings/main`
  - `POST /api/v1/settings/main`
- Live Seerr public settings:
  - `GET /api/v1/settings/public`

### Reconciliation shape

Add a narrow Seerr helper in `scripts/haac.py`:

- read the current main settings after the admin session is established
- merge only the repo-managed desired fragment:
  - `applicationUrl=https://seerr.<domain>`
- persist through `POST /api/v1/settings/main`
- verify the desired field after the write

This stays intentionally narrow. It must not overwrite unrelated Seerr main settings that the operator may manage later, and it must not introduce file-level mutation of the Seerr container config.

### Documentation

Update the README media automation contract so Seerr's automated surface explicitly includes the public application URL, not only Jellyfin and ARR service wiring.

### Validation

- `openspec validate bootstrap-seerr-main-settings-wave4`
- targeted Python unit tests for the new Seerr main-settings helper
- `python scripts/haac.py task-run -- media:post-install`
- live evidence from Seerr runtime or API showing `applicationUrl` persisted to the public domain
- browser verification that Seerr continues to expose the normal login surface rather than the setup wizard
