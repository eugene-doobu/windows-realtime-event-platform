from gan_simlab.validation.checks import build_schema_validation


def test_schema_validation_placeholder_passes() -> None:
    validation = build_schema_validation("run-123")

    assert validation.passed is True
    assert validation.checks[0].check_id == "schema_validated"

