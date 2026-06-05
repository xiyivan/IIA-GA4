import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(1, 1.8, 100)

def poly(x):
    return -0.4407*x**2 + 1.5216*x -1.0422

def reverse(x):
    return np.sqrt(0.08872327 * x - 0.0921302) + 0.03849259

plt.plot(x, poly(x))
plt.plot(x, reverse(x))
plt.show()