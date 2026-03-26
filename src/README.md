# Planned Source Layout

The repository now uses a split source tree so the Python control plane and the
C++ kernel can evolve independently.

```text
python/
  simlab/
    api/
    runner/
    schemas/
    storage/
    validation/
    visualization/

cpp/
  include/simlab/
  src/

bindings/
tests/
  python/
  cpp/

fixtures/
runtime_scenarios/
```

Suggested responsibilities:

- `python/gan_simlab/api/`
  FastAPI app and run routes

- `python/gan_simlab/runner/`
  scenario loading, subprocess entrypoints, artifact writing

- `python/gan_simlab/schemas/`
  Pydantic schemas for scenarios and artifacts

- `python/gan_simlab/storage/`
  SQLite-backed run metadata helpers

- `python/gan_simlab/validation/`
  validation checks and synthetic benchmark helpers

- `python/gan_simlab/visualization/`
  graph export utilities for debugging and inspection

- `cpp/include/simlab/` and `cpp/src/`
  kernel-facing state, graph, metrics, and round execution code

- `bindings/`
  Python extension boundary built with `pybind11`

- `fixtures/`
  public synthetic scenarios and expected assertions

- `runtime_scenarios/`
  runtime-injected private scenarios kept out of git

Keep the first implementation focused on one end-to-end run path before adding
more folders or abstractions.
