from cycle import HeatPumpCycle

refrigerants = ["R12", "R134a", "R1234yf"]
cycles = {}


for refrigerant in refrigerants:
    cycles[refrigerant] = HeatPumpCycle(refrigerant)

param_sets = {
    "vehicle_bl": {
        "Tcold": -10 + 273.15,
        "Thot": 45 + 273.15,
        "ETACOMP": 0.65,
        "FPCOND": 0.05,
        "FPEVA": 0.08,
    },
    "resident_bl": {
        "Tcold": -7 + 273.15,
        "Thot": 40 + 273.15,
        "ETACOMP": 0.75,
        "FPCOND": 0.04,
        "FPEVA": 0.04,
    },
}

active_set = "resident_bl"
p = param_sets[active_set]

print("active set %s" %active_set)
for refrigerant, cycle in cycles.items():

    cycle.solv_realistic(p["Tcold"], p["Thot"], p["ETACOMP"], p["FPCOND"], p["FPEVA"])
    print(cycle.COP_internal(), "for ", refrigerant)



