# Persona Design Rationale

## Why Persona Design Matters Here

In this repository, persona is not decoration.

Persona is part of the simulation initial condition. If persona design is weak,
the engine can still run, but the behavior will collapse toward generic,
undifferentiated agents.

The project therefore treats persona as:

- a structured population model
- a behavioral prior layer
- a source of action differences across agents
- an inspectable artifact, not hidden prompt state

This document explains the current design choices and why they were selected.

## Decision 1: Separate `persona` from `state`

We keep persona and state separate.

- `persona`: relatively stable priors
- `state`: round-to-round values like stance, trust, salience

Why:

- believable long-running behavior needs stable character structure plus
  evolving short-term state
- mixing them makes intervention effects hard to interpret

Applied in this repository:

- persona priors live in the scenario archetypes and prepared population
- current opinion dynamics still live in the kernel state arrays

Why this choice:

- aligns with the observation / memory / planning separation seen in
  Generative Agents
- keeps the `C++` kernel focused on mutable simulation state

References:

- Generative Agents: https://arxiv.org/abs/2304.03442
- OASIS Social Agent: https://docs.oasis.camel-ai.org/key_modules/social_agent

## Decision 2: Use population-aligned archetypes, not freeform characters

We generate agents from archetypes plus variation instead of writing hundreds of
fully custom personas.

Why:

- the simulation needs population structure first
- representative distributions matter more than colorful individual backstories
- this keeps scaling to 300 to 1000+ agents feasible

Applied in this repository:

- archetypes define base stance, trust, salience, activity, influence
- archetypes now also define structural and behavioral persona priors
- individual agents are generated with bounded jitter around those priors

Why this choice:

- synthetic populations should reflect target group distributions
- persona sets that are not aligned to a target population create distorted
  outcomes

References:

- Population-Aligned Persona Generation for LLM-based Social Simulation:
  https://arxiv.org/abs/2509.10127
- Generation of Synthetic Populations in Social Simulations:
  https://www.jasss.org/25/2/6.html

## Decision 3: Prefer behavior axes over direct psychometric labels

We do not use raw Big Five scores as the public simulation interface.

Instead, we use behaviorally meaningful axes such as:

- `conflict_tolerance`
- `conformity`
- `risk_aversion`
- `trust_in_officials_baseline`
- `rumor_susceptibility`
- `correction_acceptance`
- `reply_tendency`
- `post_tendency`
- `reaction_tendency`

Why:

- these map directly into action probabilities and update rules
- they are easier to explain in reports and debugging
- they avoid overstating weak psychometric validity

Why this choice:

- LLMs show socially desirable answering behavior on personality surveys
- direct personality labels are less useful than action-linked priors for this
  engine

References:

- Social desirability bias in Big Five surveys:
  https://academic.oup.com/pnasnexus/article/3/12/pgae533/7919163
- Psychometric framework for personality traits in LLMs:
  https://www.nature.com/articles/s42256-025-01115-6

## Decision 4: Keep persona layered

The current persona model is split into four practical layers.

### Structural layer

Fields:

- `age_band`
- `job_type`
- `household_stage`
- `education_level`
- `region_type`
- `income_pressure`
- `media_diet`

Purpose:

- represent social position
- influence exposure patterns and baseline incentives

### Behavioral prior layer

Fields:

- `conflict_tolerance`
- `conformity`
- `risk_aversion`
- `trust_in_officials_baseline`
- `rumor_susceptibility`
- `correction_acceptance`

Purpose:

- determine how the agent tends to respond under pressure

### Interaction-style layer

Fields:

- `reply_tendency`
- `post_tendency`
- `reaction_tendency`
- `verbosity`
- `tone_style`
- `argument_style`

Purpose:

- support later interaction and expression layers
- make visible behavior diverge even when stance is similar

### Dynamic state layer

Still separate:

- `stance`
- `trust`
- `salience`
- `activity`

Purpose:

- these change inside the simulation loop

## Decision 5: Keep LLM usage out of persona truth

LLMs are not the source of truth for persona definition.

Why:

- freeform LLM persona generation is hard to validate
- it introduces hidden non-determinism into a part of the system that should be
  inspectable
- the project needs stable, reproducible simulation inputs

Current rule:

- persona truth = structured schema fields
- future LLM usage = persona card rendering, representative expression, report
  assistance

Why this choice:

- the hot path should remain deterministic and framework-light
- richer natural language can be layered on top later without changing core
  behavior

References:

- OASIS Agent Profile:
  https://docs.oasis.camel-ai.org/user_generation/generation
- Opinion dynamics with LLM agents:
  https://arxiv.org/abs/2311.09618

## Decision 6: Make persona inspectable through artifacts

Persona should not be hidden inside the run.

Current artifact:

- `persona_snapshot.json`

Purpose:

- inspect sampled agents
- inspect group-level dominant styles
- verify that intended differences actually exist

Why this choice:

- if persona differences are not visible, they cannot be debugged
- simulation claims are much weaker when initial human-model assumptions are
  opaque

## Decision 7: Validate persona quality explicitly

Persona generation needs its own checks.

The project should evaluate at least these properties:

- population alignment
- trait diversity
- behavioral separation across groups
- seed stability
- obvious bias collapse

Recommended future artifact:

- `persona_validation.json`

Recommended future checks:

- expected group share vs generated share
- variance floors for key persona fields
- monotonic relation between persona priors and action tendencies
- stable distribution under fixed seed

## What We Deliberately Did Not Do

We did not:

- turn personas into long free-text biographies
- make the kernel depend on natural language persona descriptions
- use direct Big Five scores as the main runtime interface
- let LLMs define population truth at generation time

These choices were excluded to preserve:

- reproducibility
- inspectability
- scale
- clear causal links between persona and behavior

## Current Repository Mapping

Current implementation points:

- archetype persona fields live in
  `python/gan_simlab/schemas/scenario.py`
- persona instances are generated in
  `python/gan_simlab/runner/population.py`
- persona artifact generation lives in
  `python/gan_simlab/persona/snapshot.py`

This is still a scaffold. The next stage is to make persona priors directly
affect interaction actions like `post`, `reply`, and `react`.

## References

- Population-Aligned Persona Generation for LLM-based Social Simulation:
  https://arxiv.org/abs/2509.10127
- Generation of Synthetic Populations in Social Simulations:
  https://www.jasss.org/25/2/6.html
- Generative Agents: https://arxiv.org/abs/2304.03442
- Simulating Opinion Dynamics with Networks of LLM-based Agents:
  https://arxiv.org/abs/2311.09618
- OASIS Agent Profile:
  https://docs.oasis.camel-ai.org/user_generation/generation
- OASIS Social Agent:
  https://docs.oasis.camel-ai.org/key_modules/social_agent
- Large language models display human-like social desirability biases in Big
  Five personality surveys:
  https://academic.oup.com/pnasnexus/article/3/12/pgae533/7919163
- A psychometric framework for evaluating and shaping personality traits in
  large language models:
  https://www.nature.com/articles/s42256-025-01115-6
