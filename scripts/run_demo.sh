#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$ROOT/.matplotlib-cache}"
mkdir -p "$MPLCONFIGDIR"
python3 "$ROOT/agent/pybamm_agent.py" "simulate a 1C lithium-ion battery discharge for 3600 seconds"
python3 "$ROOT/agent/pybamm_agent.py" "compare SPM SPMe and DFN battery models"
python3 "$ROOT/agent/pybamm_agent.py" "run a C-rate parameter sweep for 0.5C 1C 2C and 3C"
python3 "$ROOT/agent/pybamm_agent.py" "run a charge discharge cycle test"
python3 "$ROOT/agent/pybamm_agent.py" "validate the battery simulation results"
python3 "$ROOT/scripts/check_submission.py"
