"""
Read task1-6_extracted.csv and plot the first and last records
on the same T-s diagram with the R134a saturation curve.
"""
import os
import csv
import numpy as np
import matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI as si

# Import the HeatPumpCycle class from cycle.py
from cycle import HeatPumpCycle

# ── paths ────────────────────────────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, "results", "task1-6_extracted.csv")

# ── read CSV and grab first & last data rows ────────────────────────────
with open(csv_path, "r") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

first = rows[0]
last  = next(r for r in rows
             if r["valve state(%)"] == "75" and r["fan state(%)"] == "25")

print("First record:",  first["File"], "| valve:", first["valve state(%)"],
      "| fan:", first["fan state(%)"], "| time:", first["Time stamp"])
print("Second record:", last["File"],  "| valve:", last["valve state(%)"],
      "| fan:", last["fan state(%)"],  "| time:", last["Time stamp"])


def row_to_cycle(row):
    """Convert a CSV row dict into a solved HeatPumpCycle, return the cycle."""
    T1 = float(row["T1r (C)"]) + 273.15
    T2 = float(row["T2r (C)"]) + 273.15
    T3 = float(row["T3r (C)"]) + 273.15
    T4 = float(row["T4r (C)"]) + 273.15
    P1 = float(row["P1 (bar)"]) * 1e5
    P2 = float(row["P2 (bar)"]) * 1e5

    cycle = HeatPumpCycle()
    cycle.solve_exp(T1, T2, T3, T4, P1, P2, FPCOND=0.05)
    return cycle


cycle_first = row_to_cycle(first)
cycle_last  = row_to_cycle(last)

# ── plot: saturation curve + both cycles ─────────────────────────────────
fluid = "R134a"

# saturation dome data
pc = si(fluid, "pcrit")
pt = si(fluid, "ptriple")
p = np.geomspace(pt, pc, 500)

ts = si("T", "P", p, "Q", 0.0, fluid)
sf = si("S", "P", p, "Q", 0.0, fluid)
sg = si("S", "P", p, "Q", 1.0, fluid)

# close the dome
T_dome = np.concatenate((ts, np.flip(ts[1:])))
s_dome = np.concatenate((sf, np.flip(sg)[1:]))

fig, ax = plt.subplots(figsize=(9, 7))
ax.plot(s_dome, T_dome, "k-", linewidth=1.2, label="Saturation curve")

# helper to draw one cycle (closed loop: 1→2→3→4→1)
def draw_cycle(ax, cycle, label, color, marker="o-"):
    res = cycle.results  # shape (4,6): [h, T, p, v, s, Q]
    s_vals = [res[i, 4] for i in range(4)]  # specific entropy
    T_vals = [res[i, 1] for i in range(4)]  # temperature
    # close the loop back to station 1
    s_vals.append(res[0, 4])
    T_vals.append(res[0, 1])
    ax.plot(s_vals, T_vals, marker, color=color, label=label,
            markersize=7, linewidth=1.8)

draw_cycle(ax, cycle_first,
           label=f"valve state:{first['valve state(%)']}%, fan state:{first['fan state(%)']}%",
           color="blue")
draw_cycle(ax, cycle_last,
           label=f"valve state:{last['valve state(%)']}%, fan state:{last['fan state(%)']}%",
           color="red")

ax.set_xlabel("Specific entropy  (kJ/kg·K)", fontsize = 20)
ax.set_ylabel("Temperature  (K)", fontsize = 20)
# ax.set_title(f"T–s Diagram — {fluid}  |  First & Last Operating Points")
ax.legend(fontsize=16)
ax.grid(True, alpha=0.3)
ax.set_xlim(800, 1800)
ax.set_ylim(250, None)

plt.tight_layout()
plt.savefig("T-s diagram.png")
plt.show()
