from CoolProp.CoolProp import PropsSI as si
import numpy as np
from matplotlib import pyplot as plt

fluids = ["R12", "R134a", "R1234yf", "CarbonDioxide"]
discription = ["CFC", "HFC", "HFO","natural"]
# fluids.pop(-1)
# discription.pop(-1)
legends = []
for i, fluid in enumerate(fluids):

    pc = si(fluid, 'pcrit')
    pt = si(fluid, 'ptriple')

    p = np.geomspace(pt, pc, 500)

    ts = si('T', 'P', p, "Q", 0.0, fluid)
    sf = si('S', 'P', p, "Q", 0.0, fluid)
    sg = si('S', 'P', p, 'Q', 1.0, fluid)

    vf = si('D', 'P', p, "Q", 0.0, fluid)
    vg = si('D', 'P', p, 'Q', 1.0, fluid)

    T = np.concatenate((ts, np.flip(ts[1:])))
    s = np.concatenate((sf, np.flip(sg)[1:]))

    plt.figure(1)
    plt.plot(s, T)

    legends.append('Satuation Line for %s, case %s' %(fluid,discription[i]))

    P = np.concatenate((p, np.flip(p[1:])))
    v = np.concatenate((vf, np.flip(vg[1:])))
    plt.figure(2)
    plt.plot(v, P)



plt.figure(1)
plt.legend(legends)
plt.xlabel('Specific entropy (kJ/kg K)')
plt.ylabel('Temperature (K)')


plt.figure(2)
plt.legend(legends)
plt.ylabel('Pressure (Pa)')
plt.xlabel('Specific Volume (kg/m^3)')

plt.show()