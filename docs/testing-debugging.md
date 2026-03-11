# Validation Strategy

## Main Principle

The key question is not whether the output text sounds plausible.

The key question is whether the simulation behaves in a controlled,
reproducible, and explainable way.

## Validation Layers

### 1. Kernel Correctness

Check the simulation kernel itself:

- deterministic output under the same seed
- valid state bounds after every round
- no impossible transitions
- stable metrics output format

Examples:

- trust stays within `[0, 1]`
- stance stays within the defined domain
- salience cannot become negative

### 2. Scenario Directionality

Check whether a known intervention moves the system in the expected direction.

Examples:

- adding a compensating measure should reduce backlash for the target group
- a fast clarification should reduce rumor persistence relative to no response
- a high-trust group should absorb official correction faster than a low-trust group

This is the most important layer for the first usable benchmark.

### 3. Internal Consistency

Check whether outputs agree with model assumptions.

Examples:

- agents with low activity should not dominate posting volume
- private-message channels should retain rumor longer than official channels
- low-trust, high-salience groups should be harder to stabilize

### 4. Batch Stability

Run the same scenario over multiple seeds and compare distributions.

Look for:

- directionally stable outcomes
- acceptable spread
- no pathological explosions

## Synthetic Validation Scenario

The public repo should ship one synthetic scenario with the same structure as a
high-sensitivity policy reform case, but without real-world references.

Suggested fixture:

- "Long-Term Public Benefit Reform"

Stakeholder groups:

- young workers
- mid-career workers
- pre-retirement households
- current beneficiaries
- government communicators
- financial commentators
- community amplifiers

Intervention variants:

- Plan A: burden increase only
- Plan B: burden increase plus targeted support
- Plan C: Plan A plus fast clarification

Expected directional checks:

- Plan B should outperform Plan A for the affected group
- delayed clarification should leave higher rumor residue than fast clarification
- groups with higher baseline trust should recover faster after clarification

## Required Outputs

Each run should produce:

- group-level stance shift
- group-level trust shift
- channel-level propagation volume
- rumor residue score
- intervention effect delta
- validation pass/fail summary

## Acceptance Criteria For The First Benchmark

The first benchmark is good enough when:

1. the same seed reproduces identical outputs
2. the expected intervention ordering holds across repeated runs
3. validation failures are explicit and machine-readable
4. a human can inspect the report and understand why a run passed or failed

## What To Avoid

Do not validate only with:

- "looks realistic"
- generated narrative quality
- one lucky run
- manual inspection without fixed criteria
