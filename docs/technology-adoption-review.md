# Technology Adoption Review

## Goal

Review whether `RAG`, `LangChain`, and `LangGraph` should be introduced into
this repository based on practical fit, not keyword collection.

The standard for adoption is simple:

- the technology must solve a real problem in this codebase
- it must fit the current architecture cleanly
- it must not weaken the deterministic simulation core

## Current Architecture Context

The repository already has a strong center of gravity:

- `FastAPI` control plane
- Python orchestration for schema loading, prepared input generation, and reports
- `C++` kernel for large-scale simulation loops
- validation-first artifact generation

This means any framework review must start with one rule:

- do not move the simulation hot path out of the `C++` kernel

## Technology Review

### RAG

#### Practical fit

`RAG` is the most natural addition.

Useful places:

- external scenario document grounding
- background material lookup during scenario preparation
- persona grounding from retrieved documents
- intervention note lookup
- report citation and evidence attachment

Why it fits:

- it helps where the project already depends on external context
- it improves traceability and explanation quality
- it does not need to touch the simulation kernel

Recommended boundary:

- use RAG before simulation and after simulation
- do not use RAG inside the round-by-round kernel loop

#### Decision

- recommended

## LangChain

### Practical fit

`LangChain` is useful only as a thin integration layer.

Useful places:

- document loaders
- text splitting
- retriever wrappers
- structured LLM output
- provider adapters for report or expression layers

Why it fits:

- it reduces glue code around document ingestion and structured outputs
- it can support a future RAG layer without changing the kernel

Why it should stay thin:

- the repository already has its own control flow
- replacing orchestration or simulation logic with framework abstractions would
  add indirection without solving the hard part

#### Decision

- conditionally recommended
- use only in ingestion, retrieval, and structured output paths

## LangGraph

### Practical fit

`LangGraph` is not a good fit for the current core.

The project's main loop is:

- dense state updates
- graph traversal
- deterministic per-round simulation
- validation against expected directional outcomes

These are kernel concerns, not agent-workflow concerns.

`LangGraph` becomes useful only if the repository later gains a clearly
separate upper layer such as:

- document interpretation workflow
- narrative extraction workflow
- representative agent expression workflow
- report assembly workflow with multiple tools or model steps

Why it does not fit the current core:

- it overlaps with orchestration already handled in Python
- it does not improve the `C++` kernel
- it risks blurring a clean deterministic boundary

#### Decision

- not recommended for the current core
- reconsider only for future interaction or expression workflows

## Final Recommendation

### Adopt now

- `RAG`
- thin `LangChain` support where it reduces ingestion or retrieval boilerplate

### Do not adopt now

- `LangGraph` in the simulation core

### Revisit later

- `LangGraph` for an upper workflow layer if the project grows a real
  interaction or expression subsystem

## Recommended Integration Order

1. add a small document-grounding path with `RAG`
2. use `LangChain` only where it simplifies document loading or structured output
3. keep the simulation kernel and validation path framework-light
4. evaluate `LangGraph` only after a real multi-step agent workflow exists

## Non-Negotiable Boundary

Regardless of framework choice, these parts should remain framework-light:

- run preparation contract
- kernel input serialization
- `C++` simulation loop
- deterministic artifact generation
- validation checks

## References

- LangGraph overview: https://docs.langchain.com/oss/python/langgraph
- LangGraph durable execution: https://docs.langchain.com/oss/python/langgraph/durable-execution
- LangChain retrieval: https://docs.langchain.com/oss/python/langchain/retrieval
- LangGraph agentic RAG: https://docs.langchain.com/oss/python/langgraph/agentic-rag
- OpenAI agent builder: https://developers.openai.com/api/docs/guides/agent-builder
- OpenAI evals: https://developers.openai.com/api/docs/guides/agent-evals
