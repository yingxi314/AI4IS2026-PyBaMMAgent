# Extended Functions

## 1. Multi-model Battery Simulation Comparison

**Description:** Compares the PyBaMM SPM, SPMe, and DFN models under the same discharge condition.

**Command:**

```bash
python3 agent/pybamm_agent.py "compare SPM SPMe and DFN battery models"
```

**Evidence:**

```text
reports/model_comparison_results.csv
reports/model_comparison_voltage.png
reports/model_comparison_report.md
```

## 2. C-rate Parameter Sweep

**Description:** Runs the same battery model at multiple C-rates and compares voltage, capacity, energy, and runtime.

**Command:**

```bash
python3 agent/pybamm_agent.py "run a C-rate parameter sweep for 0.5C 1C 2C and 3C"
```

**Evidence:**

```text
reports/parameter_sweep_results.csv
reports/parameter_sweep_voltage.png
reports/parameter_sweep_capacity.png
reports/parameter_sweep_report.md
```

## 3. Charge-discharge Cycle Protocol Simulation

**Description:** Simulates a discharge, rest, charge, and constant-voltage hold protocol.

**Command:**

```bash
python3 agent/pybamm_agent.py "run a charge discharge cycle test"
```

**Evidence:**

```text
reports/cycle_test_results.csv
reports/cycle_voltage_curve.png
reports/cycle_test_report.md
```

## 4. Automatic Engineering KPI Extraction

**Description:** Extracts voltage, capacity, energy, duration, runtime, and status indicators from the PyBaMM solution.

**Command:**

```bash
python3 agent/pybamm_agent.py "simulate a 1C lithium-ion battery discharge for 3600 seconds"
```

**Evidence:**

```text
outputs/battery_summary.txt
reports/performance_indicators_report.md
reports/battery_report.md
```

## 5. Physical Consistency and Operating-window Validation

**Description:** Checks finite values, time ordering, voltage limits, non-negative capacity, and expected discharge behavior.

**Command:**

```bash
python3 agent/pybamm_agent.py "validate the battery simulation results"
```

**Evidence:**

```text
reports/validation_report.md
scripts/check_submission.py
```
