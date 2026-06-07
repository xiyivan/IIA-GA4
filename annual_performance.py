import os
import csv
import numpy as np
import sys
import json
from datetime import datetime

_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _script_dir)

from home import Home


def weather_records(year):
    """
    Read Cambridge weather records for a given year.

    Raw temperature values in weather-raw.csv are in degrees Celsius x 10.

    Returns
    -------
    timestamps : np.ndarray
        Python datetime objects for each weather record.
    temperatures : np.ndarray
        Outdoor dry-bulb temperatures in degrees Celsius.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "weather-raw.csv")

    timestamps = []
    temps = []

    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            timestamp = datetime.strptime(row[0].strip(), "%Y-%m-%d %H:%M:%S")
            if timestamp.year == year:
                timestamps.append(timestamp)
                temps.append(float(row[1]) / 10.0)

    return np.array(timestamps, dtype=object), np.array(temps)



def data_reader(year):
    """
    Read the weather record and extract the temperature at particular year.

    Raw values in the CSV are in degrees Celsius × 10.

    Returns
    -------
    temperatures : np.ndarray
        Array of temperature values in degrees Celsius.
    """
    _, temperatures = weather_records(year)
    return temperatures

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
        condenser_water_m_dot=params.get("condenser_water_m_dot", 0.25),
        evaporator_air_m_dot=params.get("evaporator_air_m_dot", 0.60),
    )
    year = int(input("Year to be studied: "))
    temps_C = data_reader(year)

    print(f"Thermal resistance: {home.R:.4f} K/W")
    print(f"Threshold temperature: {home.calc_threshold_temp():.2f} K")
    result = home.annual_analysis(temps_C)
    print(f"Heat demand: {result['heat_demand_kWh']:.2f} kWh")
    print(f"Heat-pump electricity: {result['hp_electric_kWh']:.2f} kWh")
    print(f"Backup electricity: {result['backup_electric_kWh']:.2f} kWh")
    print(f"Total electricity required: {result['total_electric_kWh']:.2f} kWh")
    print(f"System SPF: {result['system_spf']:.3f}")
    print(
        "External-fluid exergy changes: "
        f"water={result['external_fluid_exergy_change_kWh']['condenser_water']:.2f} kWh, "
        f"air={result['external_fluid_exergy_change_kWh']['evaporator_air']:.2f} kWh"
    )
    print(f"Total cost: ${result['operating_cost']:.2f}")
