# Backlog

Priority order is `P0 > P1 > P2`.

## P0 - Core Run Path

- [ ] `CORE-001` Create Python project skeleton for FastAPI control plane
- [ ] `CORE-002` Define scenario schema and validation rules
- [ ] `CORE-003` Define run artifact contract
- [ ] `CORE-004` Create C++ kernel library skeleton
- [ ] `CORE-005` Add Python binding layer for kernel execution
- [ ] `CORE-006` Launch one simulation run as a subprocess
- [ ] `CORE-007` Write `timeline.jsonl`, `metrics.json`, `validation.json`, and `report.md`

## P0 - Kernel State Model

- [ ] `KERN-001` Define dense agent state arrays
- [ ] `KERN-002` Define narrative token representation
- [ ] `KERN-003` Implement one-round exposure step
- [ ] `KERN-004` Implement one-round stance update step
- [ ] `KERN-005` Implement intervention application
- [ ] `KERN-006` Add deterministic seed handling

## P0 - Synthetic Validation Scenario

- [ ] `VAL-001` Add one synthetic policy-reform benchmark scenario
- [ ] `VAL-002` Define expected directional outcomes for Plan A, B, and C
- [ ] `VAL-003` Implement pass/fail validation checks
- [ ] `VAL-004` Add repeated-run comparison over multiple seeds

## P1 - Scale And Observability

- [ ] `SCALE-001` Support 300-agent runs
- [ ] `SCALE-002` Support 1000-agent runs
- [ ] `SCALE-003` Add group-level metrics aggregation
- [ ] `SCALE-004` Add channel-level propagation metrics
- [ ] `SCALE-005` Add run-to-run comparison report

## P1 - Population And Graph Generation

- [ ] `POP-001` Define archetype schema
- [ ] `POP-002` Implement archetype plus variation population generator
- [ ] `POP-003` Implement multi-channel graph generation
- [ ] `POP-004` Add group summary artifact

## P2 - Usability

- [ ] `OPS-001` Add run list and artifact download endpoints
- [ ] `OPS-002` Add run cancel support
- [ ] `OPS-003` Add concise benchmark dashboard or static summary page
- [ ] `OPS-004` Document external scenario injection flow

## Deferred Use Cases

- [ ] `USE-001` Explore anonymous community post-engagement prediction as a later application layer:
      estimate view-to-like ratio or percentile performance for a post in a specific gallery using historical data and engine-derived features, without making it part of the current core scope.
