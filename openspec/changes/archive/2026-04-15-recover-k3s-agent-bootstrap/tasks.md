## 1. Implementation

- [ ] 1.1 Detect incomplete K3s worker agent state beyond `/usr/local/bin/k3s`
- [ ] 1.2 Ensure recreated or partially bootstrapped workers rerun or restart the K3s agent before waiting on `config.toml`

## 2. Validation

- [ ] 2.1 Validate the playbook syntax
- [ ] 2.2 Rerun `task configure-os` and confirm the worker nodes return to `Ready`
- [ ] 2.3 Confirm `task up` can progress past worker bootstrap again
