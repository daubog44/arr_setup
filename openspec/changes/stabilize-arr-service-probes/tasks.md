## 1. Service probe contract

- [x] 1.1 Update the ARR `/ping` probe expectations in `scripts/haac.py` to match the deployed healthy response body
- [x] 1.2 Add focused regression coverage for the accepted ARR service probe body

## 2. Verification

- [x] 2.1 Validate the change with OpenSpec and targeted Python unit tests
- [x] 2.2 Rerun `media:post-install` live and confirm it progresses beyond the ARR service probes
