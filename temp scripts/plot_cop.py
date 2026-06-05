"""
One-off script: read task1-6_extracted.csv, solve each operating point
via HeatPumpCycle.solve_exp(), then plot internal & external COP against
pressure ratio (PR = P2/P1).
"""
import csv
import numpy as np
from matplotlib import pyplot as plt
from cycle import HeatPumpCycle

CSV_PATH = "results/task1-6_extracted.csv"
FPCOND = 0.05

# ---------------------------------------------------------------------------
# 1. Read the extracted CSV
# ---------------------------------------------------------------------------
rows = []
with open(CSV_PATH, "r", newline="") as f:
    reader = csv.DictReader(f)
    for rec in reader:
        rows.append(rec)

# ---------------------------------------------------------------------------
# 2. Solve each point & collect results
# ---------------------------------------------------------------------------
# Group data by (valve, fan) for plotting with distinct markers
groups = {}  # key: (valve%, fan%) → dict of lists

for rec in rows:
    valve = rec["valve state(%)"].strip()
    fan = rec["fan state(%)"].strip()
    ts = rec["Time stamp"].strip()

    # Extract sensor values and convert units
    # CoolProp expects K and Pa; CSV has °C and bar
    T1 = float(rec["T1r (C)"]) + 273.15
    T2 = float(rec["T2r (C)"]) + 273.15
    T3 = float(rec["T3r (C)"]) + 273.15
    T4 = float(rec["T4r (C)"]) + 273.15
    P1 = float(rec["P1 (bar)"]) * 1e5
    P2 = float(rec["P2 (bar)"]) * 1e5
    T1w = float(rec["T1w (C)"])
    T2w = float(rec["T2w (C)"])
    Ic = float(rec["Ic (amp)"])
    Qc = float(rec["Qc (l/min)"])

    # Solve the cycle
    hp = HeatPumpCycle()
    hp.solve_exp(T1, T2, T3, T4, P1, P2, FPCOND)

    cop_int = hp.COP_internal()
    cop_ext = hp.COP_external(T1w, T2w, Ic, Qc)
    PR = P2 / P1

    key = (valve, fan)
    if key not in groups:
        groups[key] = {"PR": [], "COP_int": [], "COP_ext": [], "labels": []}
    groups[key]["PR"].append(PR)
    groups[key]["COP_int"].append(cop_int)
    groups[key]["COP_ext"].append(cop_ext)
    groups[key]["labels"].append(ts)

    print(
        f"[V{valve}% F{fan}% @{ts}] PR={PR:.2f}  "
        f"COP_int={cop_int:.3f}  COP_ext={cop_ext:.3f}"
    )

# ---------------------------------------------------------------------------
# 3. Plot  —  internal & external COP on the same axis
# ---------------------------------------------------------------------------
colors = plt.cm.tab10(np.linspace(0, 1, max(len(groups), 3)))

from matplotlib.legend_handler import HandlerTuple

fig, ax = plt.subplots(figsize=(11, 7))

# ── Build table-style legend: rows = valve/fan groups, cols = int | ext ──
legend_rows = []   # list of (label, (int_handle, ext_handle))

for i, ((valve, fan), data) in enumerate(sorted(groups.items())):
    c = colors[i % len(colors)]
    group_label = f"V{valve}%  F{fan}%"

    # Internal COP: filled circles, solid line
    ax.plot(data["PR"], data["COP_int"], marker="o", color=c,
            linestyle="-", markersize=8, markerfacecolor=c)
    # External COP: open squares, dashed line
    ax.plot(data["PR"], data["COP_ext"], marker="s", color=c,
            linestyle="--", markersize=8, markerfacecolor="none")

    # Annotate points with timestamps (internal only, to avoid clutter)
    for pr, cop, lbl in zip(data["PR"], data["COP_int"], data["labels"]):
        ax.annotate(lbl, (pr, cop), textcoords="offset points",
                    xytext=(5, 5), fontsize=7, color=c)

    # Proxy artists for the legend (colour-matched)
    h_int = plt.Line2D([0], [0], marker="o", color=c, linestyle="-",
                       markerfacecolor=c, markersize=8, linewidth=1.5)
    h_ext = plt.Line2D([0], [0], marker="s", color=c, linestyle="--",
                       markerfacecolor="none", markersize=8, linewidth=1.5)
    legend_rows.append((group_label, (h_int, h_ext)))

# ── Best-fit lines (linear regression on all points) ──
all_pr = np.concatenate([np.array(d["PR"]) for d in groups.values()])
all_cop_int = np.concatenate([np.array(d["COP_int"]) for d in groups.values()])
all_cop_ext = np.concatenate([np.array(d["COP_ext"]) for d in groups.values()])

# Sort so the best-fit line plots cleanly
for arr_pr, arr_cop, style, label in [
    (all_pr, all_cop_int, "-",  "COP internal fit"),
    (all_pr, all_cop_ext, "--", "COP external fit"),
]:
    order = np.argsort(arr_pr)
    x_sorted = arr_pr[order]
    y_sorted = arr_cop[order]
    coeffs = np.polyfit(x_sorted, y_sorted, deg=1)
    y_fit = np.polyval(coeffs, x_sorted)
    ax.plot(x_sorted, y_fit, linestyle=style, color="black",
            linewidth=1.2, alpha=0.7, label=label)

# ── Legend ──
# Column-header row (black, no data association)
h_header_int = plt.Line2D([0], [0], marker="o", color="black", linestyle="-",
                          markerfacecolor="black", markersize=15, linewidth=1.5)
h_header_ext = plt.Line2D([0], [0], marker="s", color="black", linestyle="--",
                          markerfacecolor="white", markersize=15, linewidth=1.5)
legend_rows.insert(0, (" Internal  External", (h_header_int, h_header_ext)))

# Add best-fit entries at the bottom
h_fit_int = plt.Line2D([0], [0], color="black", linestyle="-", linewidth=1.5,
                       alpha=0.7, marker="", label="fit int")
h_fit_ext = plt.Line2D([0], [0], color="black", linestyle="--", linewidth=1.5,
                       alpha=0.7, marker="", label="fit ext")
legend_rows.append(("Best fit", (h_fit_int, h_fit_ext)))

handles = [pair for _, pair in legend_rows]
labels  = [lab for lab, _ in legend_rows]

leg = ax.legend(handles, labels,
                handler_map={tuple: HandlerTuple(ndivide=None, pad=1.2)},
                fontsize=15, labelspacing=0.6,
                bbox_to_anchor=(1.02, 1), loc="upper left",
                title="● solid  = COP internal\n□ dashed = COP external",
                title_fontsize=15)

ax.set_xlabel("Pressure Ratio  P₂ / P₁", fontsize = 20)
ax.set_ylabel("COP", fontsize = 20)
# ax.set_title(f"Heat Pump COP vs Pressure Ratio  (FPCOND = {FPCOND})")
ax.set_ylim(bottom=0)
ax.grid(True, alpha=0.3)
fig.tight_layout()
plt.savefig("COP_vs_PR.png")
plt.show()
