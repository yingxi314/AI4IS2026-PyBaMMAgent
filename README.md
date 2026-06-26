# AI4IS2026 PyBaMM Agent

## Project Overview

This project connects an Agent to PyBaMM, an open-source battery modeling and simulation software package. The Agent parses natural-language tasks and invokes real PyBaMM workflows for lithium-ion battery simulation, model comparison, parameter sweeps, cycle testing, KPI extraction, and validation.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

## Natural Language Examples

```bash
python3 agent/pybamm_agent.py "simulate a 1C lithium-ion battery discharge for 3600 seconds"
python3 agent/pybamm_agent.py "compare SPM SPMe and DFN battery models"
python3 agent/pybamm_agent.py "run a C-rate parameter sweep for 0.5C 1C 2C and 3C"
python3 agent/pybamm_agent.py "run a charge discharge cycle test"
python3 agent/pybamm_agent.py "validate the battery simulation results"
```

Each natural-language request records the received task, parsed intent, selected workflow, target software, and parameters in `logs/natural_language_task_log.txt` and `outputs/natural_language_summary.txt`.

## Reproduce All Results

Run these commands from the project root:

```bash
bash scripts/run_demo.sh
python3 scripts/check_submission.py
```

## Generated Files

- `outputs/`: simulation summaries, numerical solutions, and basic plots
- `reports/`: Markdown reports, result tables, and visualization figures
- `logs/`: runtime metadata and natural-language parsing logs

## Extended Functions

1. Multi-model Battery Simulation Comparison
2. C-rate Parameter Sweep
3. Charge-discharge Cycle Protocol Simulation
4. Automatic Engineering KPI Extraction
5. Physical Consistency and Operating-window Validation

Commands and evidence for these functions are documented in [EXTENSIONS.md](EXTENSIONS.md).
