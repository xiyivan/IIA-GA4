import os
import csv
import numpy as np
import sys
import json

_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _script_dir)



def data_reader(year):
    """
    Read the weather record and extract the temperature at particular year.
    temperatures : np.ndarray
        Array of temperature values (in Kelvin) for the given year.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "weather-raw.csv")

    temps = []

    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            ts = row[0].strip()
            # Extract year from "YYYY-MM-DD HH:MM:SS"
            row_year = int(ts[:4])
            if row_year == year:
                temps.append(float(row[1]))
    return np.array(temps)

def thermal_resistance_calc(wall_area, material_dict, window_thickness=0.004):
    """
    Calculate the overall thermal resistance of a building wall with a window.

    material_dict : dict
        Keys are material names,
        values are thicknesses in meters.
    """
    WWR = 0.2  # Window-to-Wall Ratio

    # Load csv file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "construction_material.csv")
    conductivity = {}
    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            name = row[0].strip()
            k = float(row[1])
            conductivity[name] = k

    #Wall
    A_wall = wall_area * (1 - WWR)
    R_wall = 0.0
    for material, thickness in material_dict.items():
        k = conductivity[material]
        R_wall += thickness / (k * A_wall)

    #Window
    A_window = wall_area * WWR
    k_glass = conductivity["Window Glass (Float)"]
    R_window = window_thickness / (k_glass * A_window)

    R_total = 1.0 / (1.0 / R_wall + 1.0 / R_window)
    return R_total


def heating_rate(T_room, T_out, R):
    return (T_room - T_out) / R

def prompt_data():
    params = {}
    params["wall_area"] = float(input("Wall area (m²): "))

    print("\n--- Materials ---")
    print("Enter material name and thickness for each layer, leave empty to exit")
    materials = {}
    while True:
        name = input("Material:")
        if name == "":
            break
        thickness = float(input(f"Thickness of '{name}' (m):"))
        materials[name] = thickness
    params["materials"] = materials

    params["T_room"] = float(input("\nRoom temperature setpoint (K): "))
    params["hp_power"] = float(input("Heat pump rated power (W): "))
    params["COE"] = float(input("Cost of electricity ($/kWh): "))
    return params


def select_or_create():
    HOUSE_DIR = os.path.join(_script_dir, "house")
    name = input("House data name: ")
    path = os.path.join(HOUSE_DIR, name + ".json")
    if os.path.isfile(path):
        reuse = input(f"'{name}' exists. Reuse? [Y/n]: ").strip().lower()
        if reuse in ("", "y"):
            with open(path, "r") as f:
                return json.load(f)
        else:
            params = prompt_data()
            os.makedirs(HOUSE_DIR, exist_ok=True)
            with open(path, "w") as f:
                json.dump(params, f, indent=2)
            return params
    else:
        params = prompt_data()
        os.makedirs(HOUSE_DIR, exist_ok=True)
        with open(path, "w") as f:
            json.dump(params, f, indent=2)
        return params


# def COP_estimation(mode, Th, Tc, threshold):
#     """
#     mode1: use linear model obtained
#     mode2: calculate at each location
#     Th & Tc pass as ndarray for speedy processing
#     """
#     if mode == 1:
#         x = Th/(Th-Tc)
#         COP = np.where(x < threshold, 1, arr * 2)
#         COP = 0.6225 * x - 0.7777
#         return COP


def power_required(Qdot, ambient_threshold, critic_temperature):
    """
    Qdot: heat loss rate of the room
    ambient_threshold: temperature heating kicks in
    critic_temperature: minimum temperature can be achieved with just heat pump

    return the power of electricity required.
    """
    pass

def calc_threshold_temp(Troom, HPpower, R):
    A = R*HPpower
    return Troom + 0.38885 * A - (0.151204 * A **2 + 0.6225 * A * Troom)**0.5
    
def energy_required(year, house):
    temp_record = data_reader(year)
    



if __name__ == "__main__":
    select_or_create()
    year = input("Year to be studied")
