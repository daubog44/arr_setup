# haac-gap-discovery Specification

## Purpose
Define how the autonomous loop discovers broader HaaC stack gaps and turns those findings into evidence-backed OpenSpec changes.

## Requirements
### Requirement: Loop can discover general HaaC gaps
The autonomous loop MUST be able to identify real evidence-backed gaps across the broader homelab-as-code stack, not only in the loop runner itself.

#### Scenario: Broader stack gap discovered
- **WHEN** the loop finds a real gap in infrastructure, GitOps, security, storage, networking, automation, cross-platform tooling, or DRY/centralization
- **THEN** it MUST be allowed to create a narrow OpenSpec change for that HaaC gap

### Requirement: Discovered HaaC gaps include a proposed solution
Every discovered HaaC gap MUST include a proposed minimal solution shape, not only the problem description.

#### Scenario: OpenSpec change created from discovery
- **WHEN** the loop opens a new OpenSpec change for a HaaC gap
- **THEN** the proposal and related artifacts MUST include both the evidence and the proposed first solution

### Requirement: Missing model capabilities are fixed at the right loop layer
When the missing capability is in repo-local model behavior rather than product code, the loop MUST prefer fixing that gap through the loop's own prompting and agent scaffolding layers.

#### Scenario: Missing repo-local model capability
- **WHEN** the loop discovers that the LLM lacks a required repo-specific capability
- **THEN** the proposed solution MUST prefer prompt rules, local skills, role prompts, subagent policy, hook/bootstrap config, or runner logic before unrelated product-level workarounds
