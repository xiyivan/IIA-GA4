import os
import csv
import numpy as np
import sys
import json

_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _script_dir)

from home import Home



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


if __name__ == "__main__":
    params = select_or_create()
    home = Home(
        wall_area=params["wall_area"],
        materials=params["materials"],
        T_room=params["T_room"],
        hp_power=params["hp_power"],
        COE=params["COE"],
    )
    year = int(input("Year to be studied: "))
    temps = data_reader(year)
    print(f"Thermal resistance: {home.R:.4f} K/W")
    print(f"Threshold temperature: {home.calc_threshold_temp():.2f} K")
    home.energy_required(temps)
