## Design

### Auth strategy

The chart version currently used for Litmus (`3.28.0`) exposes internal admin credentials and an internal auth-server, but not a repo-friendly first-class Authelia OIDC configuration surface. Forcing `edge_forward_auth` in front of that chart produces a double-login flow.

The robust choice is therefore:

- publish Litmus as `app_native`
- remove the shared Authelia middleware from the route
- keep Litmus in the official public UI catalog
- verify the app login directly in browser automation

### Credentials

Litmus will use an existing secret instead of the chart-created default secret.

Behavior:

- `LITMUS_ADMIN_USERNAME` defaults to `admin`
- `LITMUS_ADMIN_PASSWORD` defaults to `AUTHELIA_ADMIN_PASSWORD` when not explicitly set
- a sealed secret in `chaos` supplies `ADMIN_USERNAME` and `ADMIN_PASSWORD`
- the Litmus Application points the chart at that secret via `existingSecret`

This keeps the credential repo-managed without hardcoding it in the Application manifest.

### Homepage

The Litmus entry remains the single canonical Chaos UI entry. The `ChaosTest` alias is removed from the ingress catalog and from the stable spec.

### Verification

HTTP verification will continue to treat Litmus as `app_native`.

Browser verification must now:

- land on `litmus.<domain>`
- confirm it is not redirected through Authelia
- log in with the repo-managed Litmus admin credential
- fail if the UI stays on the login page or renders an error banner
