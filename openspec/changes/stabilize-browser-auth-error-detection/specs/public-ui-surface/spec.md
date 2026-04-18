## MODIFIED Requirements

### Requirement: Official UI verification matches the catalog

Endpoint verification MUST evaluate exactly the official published UI surface.

#### Scenario: Browser verification fails only on user-visible route errors

- **WHEN** browser-level verification checks an enabled official UI route
- **THEN** generic route error markers such as `404 page not found`, `Bad Gateway`, `Application is not available`, and `Internal Server Error` MUST be evaluated from user-visible page text
- **AND** hidden script payloads, serialized translations, or embedded JSON blobs MUST NOT fail a healthy route by themselves
- **AND** selector-based success checks for the route type MUST still prove that the intended UI rendered
