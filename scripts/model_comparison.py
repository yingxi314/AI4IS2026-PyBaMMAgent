#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.pybamm_agent import run_model_comparison

if __name__ == "__main__":
    run_model_comparison()
