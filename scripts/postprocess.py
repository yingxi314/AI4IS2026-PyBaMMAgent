#!/usr/bin/env python3
"""Run the standard simulation and extract its performance indicators."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.pybamm_agent import run_base_simulation

if __name__ == "__main__":
    run_base_simulation()
