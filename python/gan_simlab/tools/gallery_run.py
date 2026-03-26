"""Run a gallery post-engagement simulation and write report artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gan_simlab.gallery import (
    GalleryAssertionsArtifact,
    GalleryScenario,
    build_gallery_markdown_report,
    simulate_gallery_scenario,
    validate_gallery_assertions,
)
from gan_simlab.runner.artifacts import ensure_directory, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a gallery-oriented post engagement simulation.")
    parser.add_argument("scenario", type=Path, help="Path to gallery scenario JSON")
    parser.add_argument(
        "--assertions",
        type=Path,
        help="Optional path to gallery assertion JSON",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts") / "gallery-runs" / "latest",
        help="Directory for generated artifacts",
    )
    args = parser.parse_args()

    scenario = GalleryScenario.model_validate(json.loads(args.scenario.read_text(encoding="utf-8")))
    artifact = simulate_gallery_scenario(scenario)

    output_dir = ensure_directory(args.output_dir)
    write_json(output_dir / "gallery_run.json", artifact.model_dump())

    validation = None
    if args.assertions is not None and args.assertions.exists():
        assertions = GalleryAssertionsArtifact.model_validate(json.loads(args.assertions.read_text(encoding="utf-8")))
        validation = validate_gallery_assertions(artifact=artifact, assertions=assertions)
        write_json(output_dir / "gallery_validation.json", validation.model_dump())

    (output_dir / "gallery_report.md").write_text(
        build_gallery_markdown_report(artifact, validation),
        encoding="utf-8",
    )
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
