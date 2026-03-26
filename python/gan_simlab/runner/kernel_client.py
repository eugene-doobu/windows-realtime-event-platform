"""Boundary for calling the native kernel or a local reference fallback."""

from __future__ import annotations

from statistics import fmean

try:
    import gan_simlab_cpp
except ImportError:  # pragma: no cover - exercised indirectly in local fallback flows.
    try:
        from gan_simlab import gan_simlab_cpp  # type: ignore[attr-defined]
    except ImportError:
        gan_simlab_cpp = None


def run_kernel(
    *,
    initial_state: dict[str, list[float] | list[int]],
    graph: dict[str, list[float] | list[int]],
    config: dict[str, object],
) -> dict[str, object]:
    if gan_simlab_cpp is not None:
        return gan_simlab_cpp.run_simulation(initial_state, graph, config)
    return _run_reference_kernel(initial_state=initial_state, graph=graph, config=config)


def native_kernel_available() -> bool:
    return gan_simlab_cpp is not None


def kernel_backend_name() -> str:
    return "native" if native_kernel_available() else "python_fallback"


def _run_reference_kernel(
    *,
    initial_state: dict[str, list[float] | list[int]],
    graph: dict[str, list[float] | list[int]],
    config: dict[str, object],
) -> dict[str, object]:
    state = {
        "stance": list(initial_state["stance"]),
        "trust": list(initial_state["trust"]),
        "salience": list(initial_state["salience"]),
        "susceptibility": list(initial_state["susceptibility"]),
        "activity": list(initial_state["activity"]),
        "influence": list(initial_state["influence"]),
        "group_id": list(initial_state["group_id"]),
    }

    offsets = list(graph["offsets"])
    targets = list(graph["targets"])
    weights = list(graph["weights"])
    channels = list(config["channels"])
    interventions = list(config["interventions"])

    average_exposure_weight = fmean(channel["exposure_weight"] for channel in channels) if channels else 1.0
    average_trust_penalty = fmean(channel["trust_penalty"] for channel in channels) if channels else 0.0

    round_metrics: list[dict[str, float | int]] = []

    for round_index in range(int(config["rounds"])):
        exposure_signal = [0.0] * len(state["stance"])
        stance_acc = [0.0] * len(state["stance"])
        weight_acc = [0.0] * len(state["stance"])
        total_exposures = 0
        total_posts = 0

        for source in range(len(state["stance"])):
            emission = _clamp01(
                float(state["activity"][source]) * (0.5 + (float(state["salience"][source]) * 0.5))
            )
            if emission > 0.55:
                total_posts += 1

            for edge_index in range(offsets[source], offsets[source + 1]):
                target = targets[edge_index]
                weight = weights[edge_index]
                influence_weight = weight * (0.25 + (float(state["influence"][source]) * 0.75))
                exposure_signal[target] += emission * influence_weight
                stance_acc[target] += float(state["stance"][source]) * influence_weight
                weight_acc[target] += influence_weight
                total_exposures += 1

        intervention_stance = [0.0] * len(state["stance"])
        intervention_trust = [0.0] * len(state["trust"])
        intervention_salience = [0.0] * len(state["salience"])
        rumor_push = 0.0
        clarification_push = 0.0

        for intervention in interventions:
            if int(intervention["round_index"]) != round_index:
                continue
            target_groups = set(intervention["target_group_ids"])
            applies_to_all = not target_groups
            narrative_strength = sum(float(value) for value in intervention["narrative_push"])
            if int(intervention["kind_id"]) == 3:
                rumor_push += narrative_strength
            elif int(intervention["kind_id"]) == 1:
                clarification_push += narrative_strength

            for agent_index, current_group_id in enumerate(state["group_id"]):
                if applies_to_all or current_group_id in target_groups:
                    intervention_stance[agent_index] += float(intervention["stance_delta"])
                    intervention_trust[agent_index] += float(intervention["trust_delta"])
                    intervention_salience[agent_index] += float(intervention["salience_delta"])

        for agent_index in range(len(state["stance"])):
            neighborhood_mean = (
                stance_acc[agent_index] / weight_acc[agent_index]
                if weight_acc[agent_index] > 0.0
                else float(state["stance"][agent_index])
            )
            exposure_norm = _clamp01(exposure_signal[agent_index] * 0.25 * average_exposure_weight)
            stance_delta = (
                (neighborhood_mean - float(state["stance"][agent_index]))
                * float(state["susceptibility"][agent_index])
                * (0.10 + (float(state["salience"][agent_index]) * 0.10))
            )
            trust_drag = average_trust_penalty * exposure_norm * 0.05

            state["stance"][agent_index] = _clamp(
                float(state["stance"][agent_index]) + stance_delta + intervention_stance[agent_index],
                -1.0,
                1.0,
            )
            state["trust"][agent_index] = _clamp01(
                float(state["trust"][agent_index]) + intervention_trust[agent_index] - trust_drag
            )
            state["salience"][agent_index] = _clamp01(
                float(state["salience"][agent_index]) + (0.10 * exposure_norm) + intervention_salience[agent_index] - 0.02
            )

        round_metrics.append(
            {
                "round_index": round_index,
                "total_exposures": total_exposures,
                "total_posts": total_posts,
                "mean_stance": fmean(state["stance"]) if state["stance"] else 0.0,
                "mean_trust": fmean(state["trust"]) if state["trust"] else 0.0,
                "mean_salience": fmean(state["salience"]) if state["salience"] else 0.0,
                "rumor_share": _clamp01(rumor_push),
                "clarification_share": _clamp01(clarification_push),
            }
        )

    return {"final_state": state, "round_metrics": round_metrics}


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _clamp01(value: float) -> float:
    return _clamp(value, 0.0, 1.0)
