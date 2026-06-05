#!/usr/bin/env python3
import os
import sys
import json

_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _script_dir)

from cycle import HeatPumpCycle as hpc, ExergyAnalysis




def prompt_params():
    params = {}
    params["PREF"] = float(input("reference (station 1) pressure (bar): ")) * 1e5
    params["TREF"] = float(input("reference (station 1) temperature (degC): ")) + 273.15
    params["CMPART"] = float(input("compressor pressure ratio: "))
    params["ETACOMP"] = float(input("compressor isentropic efficiency (%): ")) / 100
    params["FPCOND"] = float(input("fractional pressure loss in condenser: "))
    params["FPEVA"] = float(input("fractional pressure loss in evaporator: "))
    params["do_exergy"] = input("Include exergy analysis? [y/N]: ").strip().lower() == "y"
    if params["do_exergy"]:
        params["T1w"] = float(input("water inlet temperature (degC): ")) + 273.15
        params["T2w"] = float(input("water outlet temperature (degC): ")) + 273.15
        params["Qc"] = float(input("water volumetric flow rate (L/min): "))
        params["Ic"] = float(input("compressor current (A): "))
        params["T1a"] = float(input("air inlet temperature (degC): ")) + 273.15
        params["T2a"] = float(input("air outlet temperature (degC): ")) + 273.15
        params["T0"] = float(input("dead-state temperature (degC): ")) + 273.15
    return params


def select_or_create():
    PARAMS_DIR = os.path.join(_script_dir, "params")
    name = input("Parameter set name: ").strip()
    path = os.path.join(PARAMS_DIR, name + ".json")
    if os.path.isfile(path):
        reuse = input(f"'{name}' exists. Reuse? [Y/n]: ").strip().lower()
        if reuse in ("", "y"):
            with open(path, "r") as f:
                return json.load(f), name
        else:
            params = prompt_params()
            os.makedirs(PARAMS_DIR, exist_ok=True)
            with open(path, "w") as f:
                json.dump(params, f, indent=2)
            return params, name
    else:
        params = prompt_params()
        os.makedirs(PARAMS_DIR, exist_ok=True)
        with open(path, "w") as f:
            json.dump(params, f, indent=2)
        return params, name


def format_cycle_output(params, name, hp, results, cop):
    """Return formatted string with parameter summary and cycle results."""
    lines = []
    lines.append(f"\nParameter set: {name}")
    lines.append(f"PREF = {params['PREF']:.1f} Pa ({params['PREF']/1e5:.4f} bar)")
    lines.append(f"TREF = {params['TREF']:.2f} K ({params['TREF']-273.15:.2f} degC)")
    lines.append(f"CMPART = {params['CMPART']}")
    lines.append(f"ETACOMP= {params['ETACOMP']}")
    lines.append(f"FPCOND = {params['FPCOND']}")
    lines.append(f"FPEVA = {params['FPEVA']}")
    lines.append("")
    lines.append("Cycle Results  [h (J/kg), T (K), P (Pa), v (m3/kg), s (J/kgK), Q]")
    stn = ["Comp inlet", "Comp outlet", "Cond outlet", "Evap inlet"]
    for i, s in enumerate(stn):
        vals = "  ".join(f"{results[i,j]:.4e}" for j in range(6))
        lines.append(f"  {s:12s}: {vals}")
    lines.append("")
    lines.append(f"COP (internal) = {cop:.4f}")
    cop_ext = hp.COP_external(params.get("T1w", 0), params.get("T2w", 0),
                               params.get("Ic", 0), params.get("Qc", 0))
    lines.append(f"COP (external) = {cop_ext:.4f}")
    return "\n".join(lines)


def format_exergy_output(ex):
    """Return formatted string with exergy distribution."""
    lines = []
    lines.append("\nExergy Distribution (J/kg)")
    labels = ["Compressor", "Condenser ", "Throttle  ", "Evaporator", "Water     ", "Air       "]
    for lb, val in zip(labels, ex.exergy_distribution):
        lines.append(f"  {lb}: {val:+.4e}")
    return "\n".join(lines)


if __name__ == "__main__":
    params, name = select_or_create()
    hp = hpc()
    results = hp.solv_theory(
        params["PREF"], params["TREF"], params["CMPART"],
        params["ETACOMP"], params["FPCOND"], params["FPEVA"],
        graph=True
    )
    cop = hp.COP_internal()

    out_text = format_cycle_output(params, name, hp, results, cop)

    if params.get("do_exergy"):
        ex = ExergyAnalysis(hp, params["T1w"], params["T2w"], params["Qc"],
                            params["Ic"], params["T1a"], params["T2a"], params["T0"])
        ex.solve_exergy_loss()
        out_text += "\n\n" + format_exergy_output(ex)
        ex.plot_exergy()

    print(out_text)

    PARAMS_DIR = os.path.join(_script_dir, "params")
    out_path = os.path.join(PARAMS_DIR, name + ".out")
    with open(out_path, "w") as f:
        f.write(out_text)
    print(f"\nResults saved to: {out_path}")