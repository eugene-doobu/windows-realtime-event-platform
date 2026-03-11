# Large-Scale Agent Simulation Engine

This repository is for building a public simulation engine with a clear split:

- Python control plane for API, scenario loading, run orchestration, and reports
- C++ kernel for large-scale agent state updates and diffusion simulation

The target is not a scenario-specific app. The target is an engine that can run
high-sensitivity public-policy or social-reaction simulations when scenario data
is injected externally at runtime.

## Inspiration And Differentiation

This project is openly inspired by
[MiroFish](https://github.com/666ghj/MiroFish).

The intent is not to hide that influence. MiroFish is the benchmark that made
the target shape concrete: scenario ingestion, agent simulation, and reportable
artifacts in one workflow.

This repository is not a fork. It is a clean-room reimplementation with a
different engineering center of gravity.

For this project's goals, the main differentiators are:

- a `C++` simulation kernel for large-scale repeated computation
- a validation-first workflow with synthetic benchmark scenarios
- a public-safe engine boundary that keeps sensitive scenario packs external
- state-based large-population agents instead of prompt-heavy agent loops
- deterministic artifacts that can be inspected and regression-tested

In short: MiroFish is the reference point for the product shape, while this
repository aims to be stricter about simulation validity, public-repo hygiene,
and large-scale kernel performance.

## Current Goal

Build a simulation engine that can:

- generate and manage hundreds to thousands of distinct agents
- simulate opinion and narrative diffusion across multiple channels
- run the heavy round loop in a C++ kernel
- expose control and results through a small FastAPI service
- validate simulation behavior with synthetic benchmark scenarios

## Project Thesis

The core learning goal is not "AI chat agents."

The core learning goal is:

- C++-backed large-scale processing
- agent-based simulation at meaningful population size
- reproducible scenario execution
- validation of simulation behavior, not only plausible text output

## Public Repo Constraints

This repository stays public and domain-neutral.

- No real-world sensitive scenario files in the repo
- No real-world seed documents in the repo
- No hardcoded scenario-specific prompts in source
- Real scenarios must be injected from external files or private storage

The public repo may contain only synthetic validation scenarios that test engine
behavior.

## MVP Scope

The first working slice is intentionally small:

1. Load one synthetic scenario config
2. Generate 300 to 1000 agents from archetypes plus variation
3. Run 10 to 20 rounds in a C++ kernel
4. Output timeline and metrics artifacts
5. Check behavior against expected directional outcomes

To keep local iteration cheap, the repository also supports:

- `smoke`, `standard`, and `full` run modes
- prepared population and graph cache reuse across repeated runs
- fixed-degree graph generation instead of naive all-pairs edge sampling

## Quickstart

Create a local virtual environment and install the package in editable mode.

On Windows with VS2022:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pybind11 scikit-build-core fastapi uvicorn pydantic networkx hypothesis pytest httpx
cmd /c "call ""C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat"" -arch=x64 -host_arch=x64 >nul && ""%CD%\.venv\Scripts\python.exe"" -m pip install -e . --no-deps"
```

Run the synthetic fixture directly:

```powershell
.\.venv\Scripts\python.exe -m simlab.runner.launch fixtures/synthetic_public_issue/scenario.json --run-mode smoke
.\.venv\Scripts\python.exe -m simlab.runner.launch fixtures/synthetic_public_issue/scenario.json --run-mode standard
```

Optional runtime grounding setup:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[rag]
$env:SIMLAB_RAG_POSTGRES_DSN = "postgresql://postgres:postgres@localhost:5432/simlab"
```

Run a grounded smoke check:

```powershell
.\.venv\Scripts\python.exe -m simlab.tools.grounding_smoke
```

Run a quick size benchmark:

```powershell
.\.venv\Scripts\python.exe -m simlab.tools.benchmark_runs
```

Run the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn simlab.api.main:app --reload
```

Then create a run:

```powershell
curl -X POST http://127.0.0.1:8000/runs ^
  -H "Content-Type: application/json" ^
  -d "{\"scenario_path\":\"fixtures/synthetic_public_issue/scenario.json\",\"run_mode\":\"smoke\"}"
```

Expected artifacts:

- `run_config.json`
- `metrics.json`
- `validation.json`
- `summary.json`
- `grounding.json` when scenario grounding is enabled
- `report.md` for `standard` and `full`
- `group_influence.dot` for `standard` and `full`

## Source of Truth

- [Project Direction](./docs/positioning.md)
- [Architecture](./docs/architecture.md)
- [Persona Design Rationale](./docs/persona-design-rationale.md)
- [Technology Adoption Review](./docs/technology-adoption-review.md)
- [Validation Strategy](./docs/testing-debugging.md)
- [12 Week Roadmap](./docs/roadmap-12-weeks.md)
- [Public Repo Package](./docs/portfolio-package.md)
- [Backlog](./tasks/backlog.md)
- [Implementation Checklist](./tasks/implementation-checklist.md)
- [Today Checklist](./tasks/today-checklist.md)
- [Milestones](./tasks/milestones.md)
- [Planned Source Layout](./src/README.md)

## License

This repository is licensed under the GNU Affero General Public License v3.0.
See [LICENSE](./LICENSE).
