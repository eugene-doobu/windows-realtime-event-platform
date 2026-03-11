# Project Direction

## What This Project Is

This project is a reusable simulation engine for large-scale social reaction and
policy diffusion modeling.

It is designed to support:

- hundreds to thousands of heterogeneous agents
- multi-channel narrative spread
- intervention testing
- reproducible scenario comparison

## Relationship To MiroFish

This project is openly inspired by
[MiroFish](https://github.com/666ghj/MiroFish).

MiroFish is useful as a reference because it demonstrates a complete flow:

- ingest scenario material
- build agent context
- run multi-agent simulation
- produce artifacts that can be reviewed afterward

This repository deliberately keeps that high-level ambition while changing the
implementation priorities.

## Where This Project Tries To Improve

This project is not trying to be "better at everything." It is trying to be
better for a narrower goal:

- stronger focus on `C++` large-scale processing experience
- clearer separation between public engine code and private scenario content
- more deterministic run artifacts for repeatability and debugging
- more explicit simulation validity checks before claiming useful output
- less dependence on prompt-shaped agent behavior in the hot loop

## What This Project Is Not

This project is not:

- a hardcoded pension simulator
- a one-off Korean policy demo
- a chatbot system where every agent is an LLM call
- a public repository for sensitive real-world scenario packs

## Why The Engine Uses C++

The main personal goal is to gain real experience with C++ for large-scale
processing.

That means C++ must own the expensive, repeated computation:

- population state arrays
- influence graph traversal
- per-round exposure and update steps
- multi-run batch simulation
- metrics aggregation

Python remains the control plane because it is better for:

- FastAPI
- schema validation
- scenario ingestion
- subprocess control
- reporting
- test harnesses

## Success Criteria

The project is successful when it can:

1. simulate at least 1000 agents on one machine
2. keep runs reproducible under the same seed
3. compare multiple intervention plans on the same synthetic scenario
4. explain why the output moved in a given direction
5. pass scenario validity checks defined before the run

## Public vs Private Boundary

Public repository content:

- engine code
- synthetic validation scenarios
- generic schemas
- benchmark and validation logic
- domain-neutral examples

Private or runtime-injected content:

- real-world Korean policy scenarios
- sensitive stakeholder packs
- real seed documents
- real event timelines and intervention drafts

This boundary matters because the repository should be usable as a public engine
without turning into a public archive of sensitive real-world scenario packs.

## Immediate Focus

The next phase is not broad product design. The next phase is to make one clean,
testable vertical slice:

- one synthetic policy scenario
- one C++ kernel loop
- one FastAPI control path
- one validation report
