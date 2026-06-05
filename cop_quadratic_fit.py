"""
One-off script: read task1-6_extracted.csv, compute COP_external,
calculate Th = (T3r + T2r)/2, Tc = (T4r + T1r)/2 (all in Kelvin),
then do a quadratic fit: COP = a*x^2 + b*x + c  where x = Th/(Th-Tc).
"""

import csv
import numpy as np

CSV_PATH = "results/task1-6_extracted.csv"

# ---------------------------------------------------------------------------
# 1. Read CSV and compute COP, Th, Tc for each row
# ---------------------------------------------------------------------------
x_vals = []  # Th / (Th - Tc)
cop_vals = []

with open(CSV_PATH, "r", newline="") as f:
    reader = csv.DictReader(f)
    for rec in reader:
        # Extract raw values (°C)
        T1w = float(rec["T1w (C)"])
        T2w = float(rec["T2w (C)"])
        T1r = float(rec["T1r (C)"])
        T2r = float(rec["T2r (C)"])
        T3r = float(rec["T3r (C)"])
        T4r = float(rec["T4r (C)"])
        Ic  = float(rec["Ic (amp)"])
        Qc  = float(rec["Qc (l/min)"])

        # External COP
        W = Ic * 230.0                     # electrical power (W)
        Q = (T2w - T1w) * Qc * 4184.0 / 60.0  # heating output (W)
        COP = Q / W

        # Th and Tc in Kelvin
        Th = (T3r + T2r) / 2.0 + 273.15
        Tc = (T4r + T1r) / 2.0 + 273.15

        x = Th / (Th - Tc)

        x_vals.append(x)
        cop_vals.append(COP)

        valve = rec["valve state(%)"].strip()
        fan   = rec["fan state(%)"].strip()
        ts    = rec["Time stamp"].strip()
        print(f"[V{valve}% F{fan}% @{ts}]  Th={Th-273.15:.2f}°C  Tc={Tc-273.15:.2f}°C  "
              f"x={x:.4f}  COP={COP:.3f}")

# ---------------------------------------------------------------------------
# 2. Fits: linear & quadratic
# ---------------------------------------------------------------------------
x_arr = np.array(x_vals)
cop_arr = np.array(cop_vals)

# Quadratic fit: COP = a2*x^2 + a1*x + a0
coeffs_q = np.polyfit(x_arr, cop_arr, 2)
a2, a1, a0 = coeffs_q
cop_q_pred = np.polyval(coeffs_q, x_arr)

# Linear fit: COP = m*x + c
coeffs_l = np.polyfit(x_arr, cop_arr, 1)
m, c = coeffs_l
cop_l_pred = np.polyval(coeffs_l, x_arr)

# --- R² helper ---
def r2_score(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return 1 - ss_res / ss_tot

r2_q = r2_score(cop_arr, cop_q_pred)
r2_l = r2_score(cop_arr, cop_l_pred)

# --- Print results ---
print("\n" + "=" * 60)
print("Linear fit:   COP = m * x + c")
print(f"  m = {m:.6f}")
print(f"  c = {c:.6f}")
print(f"  R² = {r2_l:.6f}")

print("\nQuadratic fit: COP = a2 * x^2 + a1 * x + a0")
print(f"  a2 = {a2:.6f}")
print(f"  a1 = {a1:.6f}")
print(f"  a0 = {a0:.6f}")
print(f"  R² = {r2_q:.6f}")

print(f"\n  where x = Th / (Th - Tc),   Th = (T3r+T2r)/2,  Tc = (T4r+T1r)/2  [K]")
print(f"\n  R² improvement (quadratic over linear): {r2_q - r2_l:+.6f}")

# --- Side-by-side comparison ---
print("\n" + "-" * 80)
print(f"{'x':>8}  {'COP_actual':>10}  {'COP_lin':>10}  {'res_lin':>10}  {'COP_quad':>10}  {'res_quad':>10}")
print("-" * 80)
for x, cop_a, cop_l, cop_q in zip(x_vals, cop_vals, cop_l_pred, cop_q_pred):
    print(f"{x:8.4f}  {cop_a:10.3f}  {cop_l:10.3f}  {cop_a-cop_l:+10.4f}  {cop_q:10.3f}  {cop_a-cop_q:+10.4f}")
