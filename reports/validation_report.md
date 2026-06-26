# Operating-window Validation

**Result: PASS**

The checks below were applied to `outputs/battery_solution.csv`.

- PASS: time series contains at least two samples
- PASS: time contains only finite values
- PASS: time is monotonically non-decreasing
- PASS: terminal voltage contains only finite values
- PASS: minimum voltage is at least 2.0 V
- PASS: maximum voltage is at most 5.0 V
- PASS: discharged capacity is non-negative
- PASS: terminal voltage decreases during discharge
