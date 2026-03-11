# Architecture

## System Shape

The engine is split into four layers:

1. FastAPI control plane
2. scenario and run manager in Python
3. C++ simulation kernel
4. report and validation pipeline

## Layer 1: FastAPI Control Plane

Responsibilities:

- create a run from an externally supplied scenario file
- launch a subprocess for simulation
- expose run status and artifacts
- compare run outputs

Keep this layer thin. It should not contain heavy simulation logic.

## Layer 2: Python Orchestration

Responsibilities:

- parse and validate scenario schemas
- generate a population from archetypes plus variation
- build or load channel graphs
- serialize initial state into kernel input
- launch the C++ kernel
- collect artifacts and hand them to validation and reporting

Recommended runtime shape:

- FastAPI process for control
- one subprocess per simulation run
- file-based artifacts for the first version

## Layer 3: C++ Kernel

This is the core of the project.

Responsibilities:

- hold dense agent state in arrays
- run exposure, reaction, and stance updates for each round
- apply intervention events
- track per-round metrics
- support multiple repeated runs with deterministic seeds

The kernel should not depend on domain-specific scenario names.

The kernel should work on generic inputs such as:

- agent attributes
- graph edges
- channel weights
- narrative tokens
- intervention events
- random seed
- round count

## Layer 4: Validation and Reports

Responsibilities:

- compute run metrics
- compare actual vs expected directional outcomes
- flag violated invariants
- generate a short run report

Validation is a first-class output, not an afterthought.

## Core Data Model

### Agent

Each agent should have structured state, not a full free-text persona.

Minimum fields:

- id
- archetype_id
- age_band
- income_pressure
- institutional_trust
- issue_salience
- susceptibility
- influence
- activity_level
- channel_affinity
- current_stance
- current_emotion

### Graph

Support three graph layers at minimum:

- news exposure graph
- community propagation graph
- private-message graph

### Narrative Unit

Use narrative tokens instead of raw generated text inside the kernel.

Examples:

- burden_unfair
- reform_needed
- distrust_future
- clarification_accepted
- rumor_escalates

### Intervention

Minimum intervention types:

- official announcement
- clarification
- compensating measure
- rumor correction
- media amplification

## Execution Flow

1. Python loads a synthetic or external scenario
2. Python generates population and graph inputs
3. Python launches the run subprocess
4. C++ kernel simulates N rounds
5. Kernel writes artifacts
6. Python validation layer checks invariants and expected directionality
7. Python writes a concise report

## Artifact Set

The initial artifact contract should stay simple:

- `run_config.json`
- `timeline.jsonl`
- `metrics.json`
- `validation.json`

`report.md` can be added later, but it is not required for the first executable
slice.

## Non-Goals For v0

Do not build these yet:

- per-agent LLM decision loops
- distributed workers
- Redis
- vector search
- graph database
- real-time multi-user control UI
- domain-specific scenario packs in the repo
