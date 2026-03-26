"""Validation helpers for the first synthetic benchmark slice."""

from __future__ import annotations

import json
from pathlib import Path

from gan_simlab.runner.execution import RunMode
from gan_simlab.schemas.artifacts import MetricsArtifact, ValidationArtifact, ValidationCheck
from gan_simlab.schemas.scenario import Scenario


def build_schema_validation(run_id: str) -> ValidationArtifact:
    checks = [
        ValidationCheck(
            check_id="schema_validated",
            passed=True,
            actual="validated",
            expected="validated",
            message="Scenario schema passed bootstrap validation.",
        )
    ]
    return ValidationArtifact(run_id=run_id, passed=True, checks=checks)


def validate_run(
    *,
    run_id: str,
    scenario: Scenario,
    run_mode: RunMode,
    metrics: MetricsArtifact,
    final_state: dict[str, list[float] | list[int]],
    expected_assertions_path: Path,
) -> ValidationArtifact:
    checks: list[ValidationCheck] = []
    checks.extend(build_schema_validation(run_id).checks)

    if expected_assertions_path.exists():
        assertions = json.loads(expected_assertions_path.read_text(encoding="utf-8"))
        for assertion in assertions.get("checks", []):
            validation_check = _evaluate_assertion(
                assertion=assertion,
                scenario=scenario,
                run_mode=run_mode,
                metrics=metrics,
                final_state=final_state,
            )
            if validation_check is not None:
                checks.append(validation_check)

    passed = all(check.passed for check in checks)
    return ValidationArtifact(run_id=run_id, passed=passed, checks=checks)


def _evaluate_assertion(
    *,
    assertion: dict[str, object],
    scenario: Scenario,
    run_mode: RunMode,
    metrics: MetricsArtifact,
    final_state: dict[str, list[float] | list[int]],
) -> ValidationCheck | None:
    check_id = str(assertion["check_id"])
    kind = str(assertion["kind"])
    expected = assertion["expected"]

    required_run_mode = assertion.get("required_run_mode")
    if required_run_mode is not None and not _run_mode_meets_requirement(
        current=run_mode,
        required=RunMode(str(required_run_mode)),
    ):
        return None

    if kind == "bootstrap":
        return ValidationCheck(
            check_id=check_id,
            passed=True,
            actual="validated",
            expected=str(expected),
            message="Bootstrap placeholder check passed.",
        )

    if kind == "round_count":
        actual = len(metrics.round_metrics)
        return ValidationCheck(
            check_id=check_id,
            passed=actual == scenario.simulation.rounds,
            actual=actual,
            expected=scenario.simulation.rounds,
            message="Round metric count must match configured rounds.",
        )

    if kind == "positive_posts":
        actual = any(metric.total_posts > 0 for metric in metrics.round_metrics)
        return ValidationCheck(
            check_id=check_id,
            passed=actual == bool(expected),
            actual=str(actual).lower(),
            expected=str(bool(expected)).lower(),
            message="At least one round should produce posts.",
        )

    if kind == "stance_bounds":
        lower = float(assertion.get("lower", -1.0))
        upper = float(assertion.get("upper", 1.0))
        values = [float(value) for value in final_state["stance"]]
        actual = all(lower <= value <= upper for value in values)
        return ValidationCheck(
            check_id=check_id,
            passed=actual,
            actual=str(actual).lower(),
            expected="true",
            message="Final stance values must stay within configured bounds.",
        )

    if kind == "scenario_id_matches":
        actual = scenario.scenario_id
        return ValidationCheck(
            check_id=check_id,
            passed=actual == str(expected),
            actual=actual,
            expected=str(expected),
            message="Scenario metadata must match the fixture.",
        )

    if kind == "group_metric_greater_than":
        group_id = str(assertion["group_id"])
        metric_name = str(assertion["metric"])
        group_metric = next((metric for metric in metrics.group_metrics if metric.group_id == group_id), None)
        if group_metric is None:
            return ValidationCheck(
                check_id=check_id,
                passed=False,
                actual="missing_group_metric",
                expected=group_id,
                message="Target group metric was not produced.",
            )

        actual = getattr(group_metric, metric_name)
        return ValidationCheck(
            check_id=check_id,
            passed=float(actual) > float(expected),
            actual=float(actual),
            expected=float(expected),
            message="Target group metric must exceed the configured threshold.",
        )

    return None


def _run_mode_meets_requirement(*, current: RunMode, required: RunMode) -> bool:
    order = {
        RunMode.SMOKE: 0,
        RunMode.STANDARD: 1,
        RunMode.FULL: 2,
    }
    return order[current] >= order[required]
