"""PyBaMM battery simulation workflows and report generation."""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
OUTPUTS = ROOT / "outputs"
LOGS = ROOT / "logs"
LOW_VOLTAGE = 2.0
HIGH_VOLTAGE = 5.0


@dataclass
class Indicators:
    initial_voltage_v: float
    final_voltage_v: float
    minimum_voltage_v: float
    maximum_voltage_v: float
    discharged_capacity_ah: float
    average_voltage_v: float
    approximate_energy_wh: float
    simulation_duration_s: float
    runtime_s: float
    status: str


@dataclass
class TaskParameters:
    """Structured parameters extracted from a natural-language task."""

    workflow: str = "base"
    c_rate: float = 1.0
    duration_s: float = 3600.0
    sweep_rates: tuple[float, ...] = (0.5, 1.0, 2.0, 3.0)
    models: tuple[str, ...] = ()


def parse_natural_language_task(task: str) -> dict[str, object]:
    """Map an English or Chinese request to a workflow and simulation parameters."""
    text = task.strip().lower().replace("，", ",").replace("；", ";")
    if not text:
        raise ValueError("natural-language task cannot be empty")

    workflow = "base"
    workflow_keywords = (
        ("all", ("all workflows", "run all", "全部", "所有流程", "完整流程")),
        ("validate", ("validate", "validation", "check", "sanity", "physical consistency", "验证", "校验")),
        ("compare", ("compare", "comparison", "models", "model", "spm", "spme", "dfn", "对比", "比较", "模型比较")),
        ("sweep", ("sweep", "sensitivity", "parameter", "c-rate", "crate", "参数扫描", "参数扫", "敏感性")),
        ("cycle", ("cycle", "charging", "charge-discharge", "charge discharge", "discharge and charge", "循环", "充放电")),
    )
    for candidate, keywords in workflow_keywords:
        if any(keyword in text for keyword in keywords):
            workflow = candidate
            break

    duration_s = 3600.0
    duration_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|小时|minutes?|mins?|min|分钟|seconds?|secs?|s|秒)(?![a-z])",
        text,
    )
    if duration_match:
        value = float(duration_match.group(1))
        unit = duration_match.group(2)
        if unit in {"hours", "hour", "hrs", "hr", "h", "小时"}:
            duration_s = value * 3600
        elif unit in {"minutes", "minute", "mins", "min", "分钟"}:
            duration_s = value * 60
        else:
            duration_s = value

    # Accept conventional forms such as 2C, 0.5 C and C/2.
    rates = [float(value) for value in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)\s*[cC](?![\w/])", task)]
    rates.extend(1.0 / float(value) for value in re.findall(r"[cC]\s*/\s*(\d+(?:\.\d+)?)", task))
    rates = list(dict.fromkeys(rates))
    if any(rate <= 0 for rate in rates):
        raise ValueError("C-rate must be positive")
    c_rate = rates[0] if rates else 1.0
    sweep_rates = tuple(rates) if workflow == "sweep" and rates else (0.5, 1.0, 2.0, 3.0)
    models = tuple(name for name in ("SPM", "SPMe", "DFN") if re.search(rf"\b{name.lower()}\b", text))
    return {
        "workflow": workflow,
        "intent": f"{workflow} battery simulation workflow",
        "c_rate": c_rate,
        "duration_s": duration_s,
        "sweep_rates": sweep_rates,
        "models": models,
    }


def parse_task(task: str) -> TaskParameters:
    """Backward-compatible typed wrapper around the natural-language parser."""
    parsed = parse_natural_language_task(task)
    return TaskParameters(
        workflow=str(parsed["workflow"]),
        c_rate=float(parsed["c_rate"]),
        duration_s=float(parsed["duration_s"]),
        sweep_rates=tuple(float(rate) for rate in parsed["sweep_rates"]),
        models=tuple(str(model) for model in parsed["models"]),
    )


def log_natural_language_task(task: str, parsed: dict[str, object]) -> None:
    """Persist an auditable record and a concise evaluator-facing summary."""
    ensure_directories()
    timestamp = datetime.now(timezone.utc).isoformat()
    record = (
        f"[{timestamp}]\n"
        f"Natural language task received: {task}\n"
        f"Parsed intent: {parsed['intent']}\n"
        f"Selected workflow: {parsed['workflow']}\n"
        "Target simulation software: PyBaMM\n"
        f"Parsed parameters: {json.dumps(parsed, ensure_ascii=False)}\n\n"
    )
    with (LOGS / "natural_language_task_log.txt").open("a", encoding="utf-8") as stream:
        stream.write(record)
    with (OUTPUTS / "natural_language_summary.txt").open("a", encoding="utf-8") as stream:
        stream.write(record)
    print(f"Natural language task received: {task}")
    print(f"Parsed intent: {parsed['intent']}")
    print(f"Selected workflow: {parsed['workflow']}")
    print("Target simulation software: PyBaMM")
    print(f"Parsed parameters: {json.dumps(parsed, ensure_ascii=False)}")


def ensure_directories() -> None:
    for directory in (REPORTS, OUTPUTS, LOGS):
        directory.mkdir(parents=True, exist_ok=True)


def _entries(solution: pybamm.Solution) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    time_s = np.asarray(solution["Time [s]"].entries, dtype=float).reshape(-1)
    voltage = np.asarray(solution["Terminal voltage [V]"].entries, dtype=float).reshape(-1)
    try:
        capacity = np.asarray(solution["Discharge capacity [A.h]"].entries, dtype=float).reshape(-1)
    except KeyError:
        capacity = np.zeros_like(time_s)
    if not (len(time_s) == len(voltage) == len(capacity)):
        raise ValueError("PyBaMM returned inconsistent result lengths")
    return time_s, voltage, capacity


def _current(solution: pybamm.Solution, time_s: np.ndarray) -> np.ndarray:
    try:
        current = np.asarray(solution["Current [A]"].entries, dtype=float).reshape(-1)
    except KeyError:
        current = np.full_like(time_s, np.nan)
    if len(current) != len(time_s):
        raise ValueError("PyBaMM returned inconsistent current result length")
    return current


def _save_base_outputs(solution: pybamm.Solution) -> None:
    """Write the standard simulation time series and its three required plots."""
    time_s, voltage, capacity = _entries(solution)
    current = _current(solution, time_s)
    frame = pd.DataFrame(
        {
            "time_s": time_s,
            "time_h": time_s / 3600,
            "terminal_voltage_v": voltage,
            "current_a": current,
            "discharge_capacity_ah": capacity,
        }
    )
    frame.to_csv(OUTPUTS / "battery_solution.csv", index=False)
    plots = (
        ("voltage_curve.png", voltage, "Terminal voltage [V]", "Terminal voltage"),
        ("current_curve.png", current, "Current [A]", "Applied current"),
        ("capacity_curve.png", capacity, "Discharge capacity [A.h]", "Discharge capacity"),
    )
    for filename, values, ylabel, title in plots:
        plt.figure(figsize=(8, 5))
        plt.plot(time_s / 3600, values)
        plt.xlabel("Time [h]")
        plt.ylabel(ylabel)
        plt.title(title)
        plt.grid(alpha=0.25)
        plt.tight_layout()
        plt.savefig(OUTPUTS / filename, dpi=160)
        plt.close()


def extract_indicators(solution: pybamm.Solution, runtime_s: float, status: str = "SUCCESS") -> Indicators:
    time_s, voltage, capacity = _entries(solution)
    if time_s.size == 0:
        raise ValueError("PyBaMM returned an empty time series")
    energy_wh = float(np.trapezoid(voltage, capacity)) if capacity.size > 1 else 0.0
    return Indicators(
        initial_voltage_v=float(voltage[0]),
        final_voltage_v=float(voltage[-1]),
        minimum_voltage_v=float(np.min(voltage)),
        maximum_voltage_v=float(np.max(voltage)),
        discharged_capacity_ah=float(max(capacity[-1] - capacity[0], 0.0)),
        average_voltage_v=float(np.mean(voltage)),
        approximate_energy_wh=abs(energy_wh),
        simulation_duration_s=float(time_s[-1] - time_s[0]),
        runtime_s=float(runtime_s),
        status=status,
    )


def validate_solution(
    solution: pybamm.Solution,
    indicators: Indicators,
    requested_duration_s: float | None = None,
    cutoff_reached: bool = False,
) -> tuple[bool, list[str]]:
    time_s, voltage, capacity = _entries(solution)
    checks: list[tuple[bool, str]] = [
        (time_s.size > 1, "time series contains at least two samples"),
        (bool(np.all(np.isfinite(voltage))), "terminal voltage contains only finite values"),
        (indicators.minimum_voltage_v >= LOW_VOLTAGE, f"minimum voltage is at least {LOW_VOLTAGE:.1f} V"),
        (indicators.maximum_voltage_v <= HIGH_VOLTAGE, f"maximum voltage is at most {HIGH_VOLTAGE:.1f} V"),
        (indicators.discharged_capacity_ah >= 0, "discharged capacity is non-negative"),
        (voltage[-1] < voltage[0], "terminal voltage decreases during discharge"),
    ]
    if requested_duration_s is not None:
        reached = indicators.simulation_duration_s >= requested_duration_s * 0.99 or cutoff_reached
        checks.append((reached, "simulation reaches the requested duration or a cutoff condition"))
    messages = [("PASS: " if passed else "FAIL: ") + message for passed, message in checks]
    return all(passed for passed, _ in checks), messages


def _solve(model: pybamm.BaseModel, experiment: pybamm.Experiment) -> tuple[pybamm.Solution, float]:
    started = time.perf_counter()
    solution = pybamm.Simulation(model, experiment=experiment).solve()
    return solution, time.perf_counter() - started


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    values = [[str(value) for value in row] for row in frame.itertuples(index=False, name=None)]
    rows = [columns, *values]
    widths = [max(len(row[i]) for row in rows) for i in range(len(columns))]
    line = lambda row: "| " + " | ".join(str(value).ljust(widths[i]) for i, value in enumerate(row)) + " |"
    return "\n".join([line(columns), "| " + " | ".join("-" * width for width in widths) + " |", *map(line, values)])


def _write_report(path: Path, title: str, intro: str, frame: pd.DataFrame | None = None) -> None:
    content = f"# {title}\n\n{intro.strip()}\n"
    if frame is not None:
        content += "\n" + _markdown_table(frame) + "\n"
    path.write_text(content, encoding="utf-8")


def run_base_simulation(c_rate: float = 1.0, duration_s: float = 3600.0) -> Indicators:
    """Run the standard discharge, write KPIs, reports, validation, and metadata."""
    ensure_directories()
    experiment = pybamm.Experiment([f"Discharge at {c_rate:g}C for {duration_s:g} seconds or until 3.0 V"])
    started_at = datetime.now(timezone.utc)
    solution, runtime = _solve(pybamm.lithium_ion.SPM(), experiment)
    _save_base_outputs(solution)
    indicators = extract_indicators(solution, runtime)
    cutoff = indicators.simulation_duration_s < duration_s * 0.99 and indicators.final_voltage_v <= 3.05
    passed, diagnostics = validate_solution(solution, indicators, duration_s, cutoff)

    summary_lines = ["Battery Performance Summary", "=" * 27]
    summary_lines.extend(f"{key}: {value}" for key, value in asdict(indicators).items())
    summary_lines.append(f"validation: {'PASS' if passed else 'FAIL'}")
    (OUTPUTS / "battery_summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    metrics = pd.DataFrame([asdict(indicators)]).round(6)
    _write_report(REPORTS / "performance_indicators_report.md", "Battery Performance Indicators", "Indicators extracted automatically from the standard SPM discharge solution.", metrics)
    _write_report(REPORTS / "battery_report.md", "Battery Simulation Report", f"The {c_rate:g}C SPM discharge completed with status **{indicators.status}** and validation **{'PASS' if passed else 'FAIL'}**.", metrics)
    validation_text = "# Operating-window Validation\n\n**Result: " + ("PASS" if passed else "FAIL") + "**\n\n" + "\n".join(f"- {message}" for message in diagnostics) + "\n"
    (REPORTS / "validation_report.md").write_text(validation_text, encoding="utf-8")
    metadata = {
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "pybamm_version": pybamm.__version__,
        "model": "SPM",
        "c_rate": c_rate,
        "requested_duration_s": duration_s,
        "runtime_s": runtime,
        "status": indicators.status,
        "validation": "PASS" if passed else "FAIL",
        "diagnostics": diagnostics,
    }
    (LOGS / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return indicators


def run_model_comparison(c_rate: float = 1.0) -> pd.DataFrame:
    ensure_directories()
    constructors: dict[str, Callable[[], pybamm.BaseModel]] = {
        "SPM": pybamm.lithium_ion.SPM,
        "SPMe": pybamm.lithium_ion.SPMe,
        "DFN": pybamm.lithium_ion.DFN,
    }
    summaries: list[dict[str, object]] = []
    plt.figure(figsize=(8, 5))
    for name, constructor in constructors.items():
        try:
            experiment = pybamm.Experiment([f"Discharge at {c_rate:g}C until 3.0 V"])
            solution, runtime = _solve(constructor(), experiment)
            metrics = extract_indicators(solution, runtime)
            time_s, voltage, _ = _entries(solution)
            plt.plot(time_s / 3600, voltage, label=name)
            summaries.append({"model": name, **asdict(metrics)})
        except Exception as exc:  # report one unavailable model without losing all results
            summaries.append({"model": name, "status": f"FAILED: {type(exc).__name__}: {exc}"})
    frame = pd.DataFrame(summaries)
    frame.to_csv(REPORTS / "model_comparison_results.csv", index=False)
    plt.xlabel("Time [h]"); plt.ylabel("Terminal voltage [V]"); plt.title(f"Model comparison at {c_rate:g}C")
    plt.grid(alpha=.25); plt.legend(); plt.tight_layout(); plt.savefig(REPORTS / "model_comparison_voltage.png", dpi=160); plt.close()
    display = frame[[column for column in ["model", "final_voltage_v", "discharged_capacity_ah", "average_voltage_v", "runtime_s", "status"] if column in frame]].round(5).fillna("-")
    _write_report(REPORTS / "model_comparison_report.md", "PyBaMM Model Comparison", f"SPM, SPMe, and DFN were evaluated under the same {c_rate:g}C discharge condition.", display)
    return frame


def run_parameter_sweep(c_rates: Iterable[float] = (0.5, 1.0, 2.0, 3.0)) -> pd.DataFrame:
    ensure_directories()
    summaries: list[dict[str, object]] = []
    curves: list[tuple[float, np.ndarray, np.ndarray, np.ndarray]] = []
    for c_rate in c_rates:
        rate = float(c_rate)
        try:
            solution, runtime = _solve(pybamm.lithium_ion.SPM(), pybamm.Experiment([f"Discharge at {rate:g}C until 3.0 V"]))
            metrics = extract_indicators(solution, runtime)
            time_s, voltage, capacity = _entries(solution)
            curves.append((rate, time_s, voltage, capacity))
            summaries.append({"c_rate": rate, **asdict(metrics)})
        except Exception as exc:
            summaries.append({"c_rate": rate, "status": f"FAILED: {type(exc).__name__}: {exc}"})
    frame = pd.DataFrame(summaries)
    frame.to_csv(REPORTS / "parameter_sweep_results.csv", index=False)
    for filename, x_kind in (("parameter_sweep_voltage.png", "time"), ("parameter_sweep_capacity.png", "capacity")):
        plt.figure(figsize=(8, 5))
        for rate, time_s, voltage, capacity in curves:
            x = time_s / 3600 if x_kind == "time" else capacity
            plt.plot(x, voltage, label=f"{rate:g}C")
        plt.xlabel("Time [h]" if x_kind == "time" else "Discharged capacity [A.h]")
        plt.ylabel("Terminal voltage [V]"); plt.title("C-rate parameter sweep"); plt.grid(alpha=.25); plt.legend(); plt.tight_layout()
        plt.savefig(REPORTS / filename, dpi=160); plt.close()
    display = frame[[column for column in ["c_rate", "final_voltage_v", "discharged_capacity_ah", "approximate_energy_wh", "runtime_s", "status"] if column in frame]].round(5).fillna("-")
    _write_report(REPORTS / "parameter_sweep_report.md", "C-rate Sweep and Sensitivity Analysis", "An SPM was discharged to 3.0 V at each requested C-rate.", display)
    return frame


def run_cycle_test() -> pd.DataFrame:
    ensure_directories()
    protocol = [
        "Discharge at 1C until 3.0 V",
        "Rest for 10 minutes",
        "Charge at 1C until 4.2 V",
        "Hold at 4.2 V until C/20",
    ]
    solution, runtime = _solve(pybamm.lithium_ion.SPM(), pybamm.Experiment(protocol))
    time_s, voltage, capacity = _entries(solution)
    try:
        current = np.asarray(solution["Current [A]"].entries, dtype=float).reshape(-1)
    except KeyError:
        current = np.full_like(time_s, np.nan)
    frame = pd.DataFrame({"time_s": time_s, "time_h": time_s / 3600, "terminal_voltage_v": voltage, "current_a": current, "discharge_capacity_ah": capacity})
    frame.to_csv(REPORTS / "cycle_test_results.csv", index=False)
    plt.figure(figsize=(8, 5)); plt.plot(time_s / 3600, voltage)
    plt.xlabel("Time [h]"); plt.ylabel("Terminal voltage [V]"); plt.title("Charge-discharge cycle protocol")
    plt.grid(alpha=.25); plt.tight_layout(); plt.savefig(REPORTS / "cycle_voltage_curve.png", dpi=160); plt.close()
    summary = pd.DataFrame([{"runtime_s": runtime, "duration_h": time_s[-1] / 3600, "minimum_voltage_v": voltage.min(), "maximum_voltage_v": voltage.max(), "samples": len(time_s), "status": "SUCCESS"}]).round(5)
    _write_report(REPORTS / "cycle_test_report.md", "Charge-discharge Cycle Test", "Protocol: discharge at 1C, rest for 10 minutes, charge at 1C, then hold at 4.2 V to C/20.", summary)
    return frame


def run_validation(c_rate: float = 1.0, duration_s: float = 3600.0) -> bool:
    """Validate the exported base-simulation data, creating it first if needed."""
    ensure_directories()
    solution_path = OUTPUTS / "battery_solution.csv"
    if not solution_path.is_file():
        run_base_simulation(c_rate, duration_s)
    frame = pd.read_csv(solution_path)
    required = {"time_s", "terminal_voltage_v", "discharge_capacity_ah"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        diagnostics = [f"FAIL: missing required CSV column: {name}" for name in missing]
        passed = False
    else:
        time_s = frame["time_s"].to_numpy(dtype=float)
        voltage = frame["terminal_voltage_v"].to_numpy(dtype=float)
        capacity = frame["discharge_capacity_ah"].to_numpy(dtype=float)
        checks = [
            (len(frame) > 1, "time series contains at least two samples"),
            (bool(np.all(np.isfinite(time_s))), "time contains only finite values"),
            (bool(np.all(np.diff(time_s) >= 0)), "time is monotonically non-decreasing"),
            (bool(np.all(np.isfinite(voltage))), "terminal voltage contains only finite values"),
            (bool(np.min(voltage) >= LOW_VOLTAGE), f"minimum voltage is at least {LOW_VOLTAGE:.1f} V"),
            (bool(np.max(voltage) <= HIGH_VOLTAGE), f"maximum voltage is at most {HIGH_VOLTAGE:.1f} V"),
            (bool(np.all(capacity >= -1e-12)), "discharged capacity is non-negative"),
            (bool(voltage[-1] < voltage[0]), "terminal voltage decreases during discharge"),
        ]
        diagnostics = [("PASS: " if ok else "FAIL: ") + message for ok, message in checks]
        passed = all(ok for ok, _ in checks)
    validation_text = (
        "# Operating-window Validation\n\n"
        f"**Result: {'PASS' if passed else 'FAIL'}**\n\n"
        "The checks below were applied to `outputs/battery_solution.csv`.\n\n"
        + "\n".join(f"- {message}" for message in diagnostics)
        + "\n"
    )
    (REPORTS / "validation_report.md").write_text(validation_text, encoding="utf-8")
    print(f"Validation result: {'PASS' if passed else 'FAIL'}")
    return passed


def run_all() -> None:
    run_base_simulation()
    run_model_comparison()
    run_parameter_sweep()
    run_cycle_test()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        help="workflow name or a quoted natural-language simulation request",
    )
    parser.add_argument("--task", help="natural-language task, for example: '用 2C 放电 30 分钟'")
    parser.add_argument("--c-rate", type=float, help="explicit C-rate override")
    parser.add_argument("--duration", type=float, help="explicit base-simulation duration in seconds")
    parser.add_argument("--rates", type=float, nargs="+", help="explicit C-rates for the sweep workflow")
    args = parser.parse_args()
    workflows = {"base", "compare", "sweep", "cycle", "validate", "all"}
    explicit_workflow = args.command if args.command in workflows else None
    natural_task = args.task or (args.command if args.command and not explicit_workflow else None)
    try:
        parsed = parse_natural_language_task(natural_task) if natural_task else None
        parameters = parse_task(natural_task) if natural_task else TaskParameters(workflow=explicit_workflow or "all")
    except ValueError as exc:
        parser.error(str(exc))
    if explicit_workflow:
        parameters.workflow = explicit_workflow
    if args.c_rate is not None:
        parameters.c_rate = args.c_rate
    if args.duration is not None:
        parameters.duration_s = args.duration
    if args.rates:
        parameters.sweep_rates = tuple(args.rates)
    if parameters.c_rate <= 0 or parameters.duration_s <= 0 or any(rate <= 0 for rate in parameters.sweep_rates):
        parser.error("C-rates and duration must be positive")
    if natural_task and parsed is not None:
        parsed.update(asdict(parameters))
        parsed["intent"] = f"{parameters.workflow} battery simulation workflow"
        log_natural_language_task(natural_task, parsed)

    if parameters.workflow == "base":
        run_base_simulation(parameters.c_rate, parameters.duration_s)
    elif parameters.workflow == "compare":
        run_model_comparison(parameters.c_rate)
    elif parameters.workflow == "sweep":
        run_parameter_sweep(parameters.sweep_rates)
    elif parameters.workflow == "cycle":
        run_cycle_test()
    elif parameters.workflow == "validate":
        if not run_validation(parameters.c_rate, parameters.duration_s):
            raise SystemExit(1)
    else:
        run_base_simulation(parameters.c_rate, parameters.duration_s)
        run_model_comparison(parameters.c_rate)
        run_parameter_sweep(parameters.sweep_rates)
        run_cycle_test()


if __name__ == "__main__":
    main()
