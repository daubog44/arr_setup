## Design

The current verifier uses `page.textContent("body")` for app-native routes. That captures hidden script payloads and serialized translation dictionaries, which are not the same thing as what an operator sees in the browser.

This change narrows the verifier contract:

1. Read visible body text with `innerText`, not raw `textContent`, for generic route-error markers.
2. Keep the existing explicit route-marker checks (`404`, `Bad Gateway`, `Application is not available`, `Internal Server Error`) but only evaluate them against visible page text.
3. Keep selector-based success checks for app-native routes unchanged, so the verifier still proves that the expected UI actually rendered.

This stays intentionally narrow. It does not change the auth matrix, route catalog, or endpoint verification list. It only fixes the browser gate so it fails on operator-visible errors instead of hidden page payloads.
