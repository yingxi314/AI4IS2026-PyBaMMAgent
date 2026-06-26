#!/usr/bin/env python3
"""Verify that the challenge submission is complete and non-empty."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    "README.md",
    "EXTENSIONS.md",
    "requirements.txt",
    "agent/pybamm_agent.py",
    "cases/battery_discharge_case.json",
    "scripts/run_demo.sh",
    "outputs/battery_summary.txt",
    "outputs/battery_solution.csv",
    "outputs/natural_language_summary.txt",
    "reports/battery_report.md",
    "reports/performance_indicators_report.md",
    "reports/model_comparison_report.md",
    "reports/parameter_sweep_report.md",
    "reports/cycle_test_report.md",
    "reports/validation_report.md",
    "reports/model_comparison_voltage.png",
    "reports/parameter_sweep_voltage.png",
    "reports/parameter_sweep_capacity.png",
    "reports/cycle_voltage_curve.png",
    "logs/natural_language_task_log.txt",
    "logs/run_metadata.json",
]

REQUIRED_TEXT = {
    "agent/pybamm_agent.py": ["parse_natural_language_task", "pybamm.Simulation"],
    "EXTENSIONS.md": [
        "Multi-model Battery Simulation Comparison",
        "C-rate Parameter Sweep",
        "Charge-discharge Cycle Protocol Simulation",
        "Automatic Engineering KPI Extraction",
        "Physical Consistency and Operating-window Validation",
    ],
    "logs/natural_language_task_log.txt": ["Selected workflow", "PyBaMM"],
}


def main() -> None:
    missing: list[str] = []
    empty: list[str] = []
    missing_text: list[str] = []

    for name in EXPECTED:
        path = ROOT / name
        if not path.is_file():
            missing.append(name)
        elif path.stat().st_size == 0:
            empty.append(name)

    for name, required_values in REQUIRED_TEXT.items():
        path = ROOT / name
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for value in required_values:
            if value not in content:
                missing_text.append(f"{name}: {value}")

    if missing or empty or missing_text:
        lines = ["Submission package check failed."]
        if missing:
            lines.extend(["Missing files:", *(f"- {name}" for name in missing)])
        if empty:
            lines.extend(["Empty files:", *(f"- {name}" for name in empty)])
        if missing_text:
            lines.extend(["Missing required text:", *(f"- {item}" for item in missing_text)])
        raise SystemExit("\n".join(lines))

    print("PASS: submission package is complete and reproducible")


if __name__ == "__main__":
    main()
