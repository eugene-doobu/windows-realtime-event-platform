# Today Checklist

This is the immediate execution list for the current stretch of work.

Work top to bottom. Do not broaden scope while this list is open.

## 1. Persona Validation

- [x] Add `persona_validation.json`
- [x] Record expected vs actual group shares
- [x] Record variance for `conflict_tolerance`
- [x] Record variance for `reply_tendency`
- [x] Record dominant `tone_style` and `argument_style` per group
- [x] Fail when persona generation collapses to near-identical priors
- [x] Add tests for fixed-seed persona reproducibility

## 2. Interaction Schema

- [x] Create `python/gan_simlab/interaction/`
- [x] Define `AgentAction`
- [x] Define `Message`
- [x] Define `Reaction`
- [x] Define `Thread`
- [x] Decide deterministic round-level IDs for threads and messages
- [x] Add artifact schema for `threads.jsonl`
- [x] Add artifact schema for `interaction_summary.json`

## 3. Active Agent Selection

- [x] Select active agents per round from kernel outputs
- [x] Weight activation by `activity`
- [x] Weight activation by `salience`
- [x] Add small weight from `influence`
- [x] Keep selection deterministic under the run seed
- [x] Add tests that `high activity + high salience` groups activate more

## 4. Persona-Driven Action Choice

- [x] Map `post_tendency` into post probability
- [x] Map `reply_tendency` into reply probability
- [x] Map `reaction_tendency` into react probability
- [x] Map `conflict_tolerance` into disagreement escalation
- [x] Map `trust_in_officials_baseline` into clarification response
- [x] Map `rumor_susceptibility` into rumor spread response
- [x] Add tests that groups diverge in action mix

## 5. First Interaction Artifacts

- [x] Emit at least one thread on `standard` runs
- [x] Emit bounded thread volume on `smoke` runs
- [x] Write `threads.jsonl`
- [x] Write `interaction_summary.json`
- [x] Expose both through the API
- [x] Add them to `available_files`

## 6. First Expression Pass

- [x] Create `python/gan_simlab/expression/`
- [x] Add template renderer for `post`
- [x] Add template renderer for `reply`
- [x] Use `tone_style`
- [x] Use `argument_style`
- [x] Use `verbosity`
- [x] Write `conversation.jsonl`
- [x] Add representative conversation lines to `report.md`

## 7. Final Checks Before Stopping

- [x] Run full test suite
- [x] Run one `smoke` grounded scenario
- [x] Run one `standard` grounded scenario
- [x] Confirm `persona_snapshot.json` still exists
- [x] Confirm `threads.jsonl` exists on `standard`
- [x] Confirm `conversation.jsonl` exists on `standard`
- [x] Confirm report contains validation, grounding, persona, and interaction sections
