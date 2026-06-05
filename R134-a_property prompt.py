from CoolProp.CoolProp import PropsSI as si
import numpy as np
from matplotlib import pyplot as plt

fluid = "R134a"

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

# plt.plot(s, T)
# plt.xlabel('Specific entropy (kJ/kg K)')
# plt.ylabel('Temperature (K)')
# plt.title('Satuation Line for %s' %fluid)

P = np.concatenate((p, np.flip(p[1:])))
v = np.concatenate((vf, np.flip(vg[1:])))

plt.plot(v, P)
plt.ylabel('Pressure (Pa)')
plt.xlabel('Specific Volume (kg/m^3)')
plt.show()