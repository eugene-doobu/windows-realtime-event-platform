# Implementation Checklist

This checklist is meant to support long stretches of autonomous work without
re-deciding the project shape every hour.

Use it as the primary execution list. Keep `backlog.md` as the broad queue and
this file as the practical build order.

## Working Rule

- keep the `C++` kernel deterministic
- keep real scenarios external to the public repo
- prefer visible artifacts over hidden state
- make each new layer testable before adding the next one

## A. Baseline Engine And Grounding

- [x] `A-001` Scenario schema supports runtime-injected synthetic scenarios
- [x] `A-002` Native `C++` kernel path builds and runs from Python
- [x] `A-003` FastAPI control plane can create and inspect runs
- [x] `A-004` Validation artifacts exist and pass on the synthetic fixture
- [x] `A-005` Run modes (`smoke`, `standard`, `full`) reduce iteration cost
- [x] `A-006` Prepared population and graph inputs are cached
- [x] `A-007` Grounding path supports `Markdown`, `JSON`, and `TXT`
- [x] `A-008` Grounding uses local `Postgres + pgvector`
- [x] `A-009` Grounding artifacts are written and exposed by the API

## B. Persona Foundation

- [x] `B-001` Archetypes include structural persona priors
- [x] `B-002` Archetypes include behavioral priors
- [x] `B-003` Archetypes include interaction-style priors
- [x] `B-004` Persona defaults are derived consistently from base simulation values
- [x] `B-005` Prepared population includes persona instance fields per agent
- [x] `B-006` `persona_snapshot.json` is generated for each run
- [x] `B-007` Report includes a concise persona snapshot section
- [x] `B-008` API exposes `persona_snapshot`

## C. Persona Validation

- [x] `C-001` Add explicit `persona_validation.json`
- [x] `C-002` Compare expected group shares against generated group shares
- [x] `C-003` Add minimum variance checks for `conflict_tolerance`
- [x] `C-004` Add minimum variance checks for `reply_tendency`
- [x] `C-005` Add dominant-style sanity checks per group
- [x] `C-006` Add fixed-seed reproducibility test for persona generation
- [x] `C-007` Add cross-seed distribution stability test
- [x] `C-008` Add warning when all groups collapse into similar tone or argument styles

## D. Interaction Layer v1

- [x] `D-001` Add `python/gan_simlab/interaction/`
- [x] `D-002` Define `AgentAction` schema
- [x] `D-003` Define `Thread` schema
- [x] `D-004` Define `Message` schema
- [x] `D-005` Define `Reaction` schema
- [x] `D-006` Select active agents per round from kernel outputs
- [x] `D-007` Make activity selection depend on `activity` and `salience`
- [x] `D-008` Make action choice depend on persona priors
- [x] `D-009` Add `ignore` as a first-class action
- [x] `D-010` Add `post` action
- [x] `D-011` Add `reply` action
- [x] `D-012` Add `react` action
- [x] `D-013` Write `threads.jsonl`
- [x] `D-014` Write `interaction_summary.json`
- [x] `D-015` Keep interaction generation deterministic under fixed seed

## E. Persona-Driven Behavior

- [x] `E-001` Map `reply_tendency` into reply probability
- [x] `E-002` Map `post_tendency` into post probability
- [x] `E-003` Map `reaction_tendency` into react probability
- [x] `E-004` Map `conflict_tolerance` into disagreement response strength
- [x] `E-005` Map `conformity` into herd-following response strength
- [x] `E-006` Map `trust_in_officials_baseline` into clarification uptake
- [x] `E-007` Map `rumor_susceptibility` into rumor acceptance tendency
- [x] `E-008` Map `correction_acceptance` into fact-check acceptance tendency
- [x] `E-009` Use `media_diet` to bias which channels get inspected first
- [x] `E-010` Add unit tests that prove groups with different priors behave differently

## F. Expression Layer v1

- [x] `F-001` Add `python/gan_simlab/expression/`
- [x] `F-002` Define a template renderer for `post`
- [x] `F-003` Define a template renderer for `reply`
- [x] `F-004` Define tone templates keyed by `tone_style`
- [x] `F-005` Define argument templates keyed by `argument_style`
- [x] `F-006` Make verbosity affect message length
- [x] `F-007` Write `conversation.jsonl`
- [x] `F-008` Add representative messages to `report.md`
- [x] `F-009` Keep expression deterministic in v1
- [x] `F-010` Add tests for tone and argument-style divergence

## G. Interaction Validation

- [x] `G-001` Add invariant that each round produces bounded interaction volume
- [x] `G-002` Add invariant that high `reply_tendency` groups reply more often
- [x] `G-003` Add invariant that low `trust_in_officials_baseline` groups accept clarification less often
- [x] `G-004` Add invariant that high `rumor_susceptibility` groups amplify rumor more often
- [x] `G-005` Add invariant that low `verbosity` groups emit shorter messages
- [x] `G-006` Add round-level action distribution metrics
- [x] `G-007` Add per-group action distribution metrics

## H. Grounding Hardening

- [x] `H-001` Cache embeddings by document hash
- [x] `H-002` Add grounding failure classification to artifacts
- [x] `H-003` Add retrieval tests against known synthetic snippets
- [x] `H-004` Add report section for retrieved evidence by intervention
- [x] `H-005` Add report section for retrieved evidence by narrative token
- [x] `H-006` Add grounding smoke test script

## I. Kernel And Scale

- [x] `I-001` Add kernel benchmark script for `100`, `300`, `1000` agents
- [x] `I-002` Record per-run execution time in artifacts
- [x] `I-003` Record graph edge count in artifacts
- [x] `I-004` Add memory footprint estimate in summary
- [x] `I-005` Verify `1000` agents complete reliably under `standard`
- [x] `I-006` Verify `3000` agents under a benchmark mode
- [x] `I-007` Profile graph generation vs kernel execution cost

## J. Analysis And Visualization

- [x] `J-001` Add group action summary chart data
- [x] `J-002` Add interaction graph export for representative threads
- [x] `J-003` Add round-by-round group movement summary
- [x] `J-004` Add narrative dominance summary by round
- [ ] `J-005` Add comparison artifact between two runs

## K. Control Plane Hardening

- [x] `K-001` Run API should launch simulations as subprocesses again
- [x] `K-002` Persist pending vs completed vs failed status
- [x] `K-003` Return early failure reason when grounding setup is missing
- [ ] `K-004` Add artifact download endpoint
- [ ] `K-005` Add run comparison endpoint

## L. Deferred But Likely

- [ ] `L-001` Introduce optional LLM-based representative expression
- [ ] `L-002` Introduce optional retrieval-assisted expression
- [ ] `L-003` Add persona cards for sampled agents
- [ ] `L-004` Add interaction scenes beyond forum-style threads
- [ ] `L-005` Add later use case for anonymous community engagement prediction

## Exit Criteria For The Next Meaningful Demo

The project is ready for the next public-quality demo when:

- [x] persona priors measurably affect interaction behavior
- [x] runs produce `threads.jsonl` and `conversation.jsonl`
- [x] reports show both validation and representative interactions
- [x] the same seed reproduces the same interaction structure
- [ ] a second person can run the synthetic scenario and inspect the result
