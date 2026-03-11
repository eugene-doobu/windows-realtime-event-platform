# 12 Week Roadmap

## Phase 1: Kernel Skeleton And Run Path

### Weeks 1-2

- define scenario schema
- define agent state schema
- define run artifact contract
- scaffold FastAPI control plane
- scaffold C++ kernel library and binding layer

### Weeks 3-4

- implement one round loop in C++
- support 300-agent synthetic runs
- write artifacts to disk
- expose start and status endpoints

Exit criteria:

- one run can execute end-to-end from FastAPI to artifacts

## Phase 2: Population Scale And Validation

### Weeks 5-6

- implement archetype plus variation population generation
- support 1000-agent runs
- add multi-channel graph input
- add intervention event application

### Weeks 7-8

- implement validation checks
- add the synthetic benchmark scenario
- compare three intervention variants
- add repeated seed runs

Exit criteria:

- one benchmark scenario produces a validation report with pass/fail checks

## Phase 3: Usability And Reporting

### Weeks 9-10

- generate concise run summaries
- compare runs side by side
- improve metrics and timeline output
- tighten run reproducibility controls

### Weeks 11-12

- clean public repo boundaries
- document external scenario injection
- prepare one public demo with only synthetic data
- prepare one private workflow for sensitive scenarios

Exit criteria:

- public repo clearly demonstrates the engine without containing sensitive scenario content
