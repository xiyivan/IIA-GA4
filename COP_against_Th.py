from cycle import HeatPumpCycle
from matplotlib import pyplot as plt
import numpy as np

cycle = HeatPumpCycle()
results = []

Params = {'PREF': 4.9846e5, 'TREF': 288.969, 'ETACOMP': 0.81204,
           'FPCOND': 0.05, 'FPEVA': 0.08228}

for i in range(20):
    CMPART = 2 + i * 0.1
    cycle.solv_theory(CMPART=CMPART, **Params)
    results.append([cycle.T3 / (cycle.T3 - cycle.T1), cycle.COP_internal()])

x, COP = np.array(results).T

# linear fit
a, b = np.polyfit(x, COP, 1)
COP_fit = a * x + b
r2 = np.corrcoef(COP, COP_fit)[0, 1] ** 2

print(f'COP = {a:.4f}·x + {b:.4f}  (R² = {r2:.4f})')

# plot
plt.plot(x, COP, 'o', label='Data')
plt.plot(x, COP_fit, label=f'Linear fit')
plt.xlabel('$T_h / (T_h - T_c)$')
plt.ylabel('COP')
plt.legend()
plt.show()