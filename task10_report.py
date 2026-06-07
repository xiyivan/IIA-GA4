#!/usr/bin/env python3
import argparse
import json
import os

import matplotlib.pyplot as plt
import numpy as np

from annual_performance import weather_records
from home import Home


COMPONENTS = ("compressor", "condenser", "throttle", "evaporator")
COMPONENT_COLORS = {
    "compressor": "#4E79A7",
    "condenser": "#F28E2B",
    "throttle": "#59A14F",
    "evaporator": "#B07AA1",
}


def load_home(path):
    with open(path, "r") as f:
        params = json.load(f)
    return Home(
        wall_area=params["wall_area"],
        materials=params["materials"],
        T_room=params["T_room"],
        hp_power=params["hp_power"],
        COE=params["COE"],
        condenser_water_m_dot=params.get("condenser_water_m_dot", 0.25),
        evaporator_air_m_dot=params.get("evaporator_air_m_dot", 0.60),
    ), params


def month_masks(timestamps):
    months = np.array([ts.month for ts in timestamps])
    return [months == month for month in range(1, 13)]


def monthly_analyses(home, temperatures, masks, dt_hours, T0):
    return [
        home.annual_analysis(temperatures[mask], dt_hours=dt_hours, T0=T0)
        for mask in masks
    ]


def plot_monthly_energy(months, monthly, output_dir):
    hp_electric = np.array([m["hp_electric_kWh"] for m in monthly])
    backup_electric = np.array([m["backup_electric_kWh"] for m in monthly])
    heat_demand = np.array([m["heat_demand_kWh"] for m in monthly])

    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.bar(months, hp_electric, label="Heat-pump electricity", color="#4E79A7")
    ax1.bar(months, backup_electric, bottom=hp_electric,
            label="Resistance backup electricity", color="#E15759")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Electricity input (kWh/month)")
    ax1.set_xticks(months)
    ax1.set_ylim(0, max((hp_electric + backup_electric).max() * 1.18, 1.0))
    ax1.grid(axis="y", alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(months, heat_demand, color="#2F2F2F", marker="o",
             linewidth=1.5, label="Heat demand")
    ax2.set_ylabel("Heat demand (kWh/month)")
    ax2.set_ylim(0, max(heat_demand.max() * 1.18, 1.0))

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right")
    ax1.set_title("Monthly heating demand and electricity input")
    fig.tight_layout()
    path = os.path.join(output_dir, "task10_monthly_energy.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_cop_curve(result, output_dir):
    series = result["series"]
    active = np.isfinite(series["cop"])
    Tout = series["Tout_C"][active]
    cop = series["cop"][active]
    demand = series["heat_demand_W"][active] / 1000.0

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.scatter(Tout, cop, s=8, alpha=0.22, color="#4E79A7", label="COP")
    ax1.set_xlabel("Outdoor temperature (degC)")
    ax1.set_ylabel("Heat-pump COP")
    ax1.grid(alpha=0.3)

    bins = np.arange(np.floor(Tout.min()), np.ceil(Tout.max()) + 1)
    bin_centres = []
    bin_cops = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (Tout >= lo) & (Tout < hi)
        if np.any(mask):
            bin_centres.append((lo + hi) / 2)
            bin_cops.append(np.mean(cop[mask]))
    ax1.plot(bin_centres, bin_cops, color="#1F4E79", linewidth=2,
             label="1 degC bin mean")

    ax2 = ax1.twinx()
    ax2.scatter(Tout, demand, s=8, alpha=0.12, color="#E15759",
                label="Heat demand")
    ax2.set_ylabel("Heat demand (kW)")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right")
    ax1.set_title("COP and heat demand versus outdoor temperature")
    fig.tight_layout()
    path = os.path.join(output_dir, "task10_cop_vs_outdoor_temperature.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_monthly_exergy(months, monthly, output_dir):
    fig, ax = plt.subplots(figsize=(9, 5))
    bottom = np.zeros(len(months))
    for component in COMPONENTS:
        values = np.array([m["component_loss_kWh"][component] for m in monthly])
        ax.bar(months, values, bottom=bottom, label=component.capitalize(),
               color=COMPONENT_COLORS[component])
        bottom += values
    ax.set_xlabel("Month")
    ax.set_ylabel("Exergy destruction (kWh/month)")
    ax.set_xticks(months)
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    ax.set_title("Monthly heat-pump exergy destruction by component")
    fig.tight_layout()
    path = os.path.join(output_dir, "task10_monthly_exergy.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_weather_histogram(temperatures, room_setpoint_C, output_dir):
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.hist(temperatures, bins=np.arange(np.floor(temperatures.min()),
                                         np.ceil(temperatures.max()) + 1),
            color="#4E79A7", alpha=0.8)
    ax.axvline(room_setpoint_C, color="#E15759", linestyle="--",
               linewidth=2, label="Room setpoint")
    ax.set_xlabel("Outdoor temperature (degC)")
    ax.set_ylabel("Number of half-hour records")
    ax.set_title("Cambridge outdoor temperature distribution")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    path = os.path.join(output_dir, "task10_weather_histogram.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_load_duration(result, output_dir):
    series = result["series"]
    demand = np.sort(series["heat_demand_W"] / 1000.0)[::-1]
    hp_heat = np.sort(series["hp_heat_W"] / 1000.0)[::-1]
    hours = np.arange(len(demand)) * result["dt_hours"]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(hours, demand, color="#2F2F2F", linewidth=2, label="Building heat demand")
    ax.plot(hours, hp_heat, color="#4E79A7", linewidth=1.8,
            label="Heat supplied by heat pump")
    ax.set_xlabel("Hours exceeded")
    ax.set_ylabel("Heating rate (kW)")
    ax.set_title("Heating load-duration curve")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    path = os.path.join(output_dir, "task10_load_duration.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_monthly_spf(months, monthly, output_dir):
    hp_spf = np.array([m["hp_spf"] for m in monthly])
    system_spf = np.array([m["system_spf"] for m in monthly])
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(months, hp_spf, marker="o", color="#4E79A7",
            label="Heat-pump SPF")
    ax.plot(months, system_spf, marker="s", color="#59A14F",
            linestyle="--", label="System SPF")
    ax.set_xlabel("Month")
    ax.set_ylabel("Monthly SPF")
    ax.set_xticks(months)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.3)
    ax.legend()
    ax.set_title("Monthly seasonal performance factor")
    fig.tight_layout()
    path = os.path.join(output_dir, "task10_monthly_spf.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_annual_exergy(annual, output_dir):
    values = [annual["component_loss_kWh"][component] for component in COMPONENTS]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar([c.capitalize() for c in COMPONENTS], values,
                  color=[COMPONENT_COLORS[c] for c in COMPONENTS])
    ax.set_ylabel("Annual exergy destruction (kWh)")
    ax.grid(axis="y", alpha=0.3)
    ax.set_title("Annual heat-pump exergy destruction by component")
    for bar in bars:
        value = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, value,
                f"{value:.1f}", ha="center", va="bottom")
    fig.tight_layout()
    path = os.path.join(output_dir, "task10_annual_exergy.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_runtime_modes(months, monthly, dt_hours, output_dir):
    active = np.array([m["active_records"] * dt_hours for m in monthly])
    backup = np.array([m["backup_records"] * dt_hours for m in monthly])
    inactive = np.array([m["inactive_records"] * dt_hours for m in monthly])

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(months, active - backup, label="Heat pump only", color="#4E79A7")
    ax.bar(months, backup, bottom=active - backup,
           label="Heat pump plus backup", color="#E15759")
    ax.bar(months, inactive, bottom=active,
           label="No heating required", color="#D9D9D9")
    ax.set_xlabel("Month")
    ax.set_ylabel("Hours")
    ax.set_xticks(months)
    ax.set_ylim(0, max((active + inactive).max() * 1.08, 1.0))
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    ax.set_title("Heating operating modes")
    fig.tight_layout()
    path = os.path.join(output_dir, "task10_runtime_modes.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def write_summary(path, year, params, home, annual, plot_paths):
    lines = [
        "# Task 10 annual heat-pump analysis",
        "",
        "This summary follows the handout Task 10 approach: heating demand is",
        "proportional to indoor-outdoor temperature difference, no heating is",
        "required when outdoor temperature exceeds the room setpoint, and an",
        "undersized heat pump is supplemented by resistance heating.",
        "",
        "## Inputs",
        "",
        f"- Weather year: {year}",
        f"- Room setpoint: {params['T_room']:.2f} K ({params['T_room'] - 273.15:.2f} degC)",
        f"- Heat-pump electrical rating: {params['hp_power']:.1f} W",
        f"- Electricity cost: {params['COE']:.3f} per kWh",
        f"- Wall/window thermal resistance: {home.R:.6f} K/W",
        f"- Condenser water mass flow: {home.condenser_water_m_dot:.3f} kg/s",
        f"- Evaporator air mass flow: {home.evaporator_air_m_dot:.3f} kg/s",
        f"- Balance temperature: {home.calc_threshold_temp() - 273.15:.2f} degC",
        "",
        "## Annual results",
        "",
        f"- Heat demand: {annual['heat_demand_kWh']:.1f} kWh",
        f"- Heat delivered by heat pump: {annual['hp_heat_kWh']:.1f} kWh",
        f"- Heat delivered by backup resistance: {annual['backup_heat_kWh']:.1f} kWh",
        f"- Heat-pump electricity: {annual['hp_electric_kWh']:.1f} kWh",
        f"- Backup electricity: {annual['backup_electric_kWh']:.1f} kWh",
        f"- Total electricity: {annual['total_electric_kWh']:.1f} kWh",
        f"- Operating cost: {annual['operating_cost']:.2f}",
        f"- Heat-pump SPF: {annual['hp_spf']:.3f}",
        f"- System SPF including backup: {annual['system_spf']:.3f}",
        f"- Heat-pump active hours: {annual['active_records'] * annual['dt_hours']:.1f} h",
        f"- No-heating hours: {annual['inactive_records'] * annual['dt_hours']:.1f} h",
        f"- Backup-heater hours: {annual['backup_records'] * annual['dt_hours']:.1f} h",
        "",
        "## Annual heat-pump exergy destruction",
        "",
        "Condenser and evaporator values include the sensible exergy change",
        "of the water and air streams, using the mass-flow assumptions above.",
        "",
    ]
    for component in COMPONENTS:
        lines.append(
            f"- {component.capitalize()}: {annual['component_loss_kWh'][component]:.1f} kWh"
        )
    lines.extend([
        f"- Total: {annual['total_loss_kWh']:.1f} kWh",
        f"- Condenser water exergy gain: {annual['external_fluid_exergy_change_kWh']['condenser_water']:.1f} kWh",
        f"- Evaporator air exergy change: {annual['external_fluid_exergy_change_kWh']['evaporator_air']:.1f} kWh",
        f"- External-fluid approach warnings: {annual['external_limit_records']}",
        "",
        "## Plots",
        "",
    ])
    for plot_path in plot_paths:
        lines.append(f"- {os.path.basename(plot_path)}")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Generate Task 10 report plots.")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--house", default=os.path.join("house", "test.json"))
    parser.add_argument("--output-dir", default=os.path.join("results", "task10_report"))
    parser.add_argument("--dt-hours", type=float, default=0.5)
    parser.add_argument("--T0", default="outdoor")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    house_path = args.house
    if not os.path.isabs(house_path):
        house_path = os.path.join(script_dir, house_path)
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(script_dir, output_dir)
    os.makedirs(output_dir, exist_ok=True)

    home, params = load_home(house_path)
    timestamps, temperatures = weather_records(args.year)
    masks = month_masks(timestamps)
    annual = home.annual_analysis(temperatures, dt_hours=args.dt_hours, T0=args.T0)
    monthly = monthly_analyses(home, temperatures, masks, args.dt_hours, args.T0)
    months = np.arange(1, 13)

    plot_paths = [
        plot_weather_histogram(temperatures, params["T_room"] - 273.15, output_dir),
        plot_load_duration(annual, output_dir),
        plot_monthly_spf(months, monthly, output_dir),
        plot_monthly_energy(months, monthly, output_dir),
        plot_cop_curve(annual, output_dir),
        plot_monthly_exergy(months, monthly, output_dir),
        plot_annual_exergy(annual, output_dir),
        plot_runtime_modes(months, monthly, args.dt_hours, output_dir),
    ]
    summary_path = os.path.join(output_dir, "task10_summary.md")
    write_summary(summary_path, args.year, params, home, annual, plot_paths)

    print(f"Task 10 analysis written to: {output_dir}")
    print(f"Summary: {summary_path}")
    print(f"System SPF: {annual['system_spf']:.3f}")
    print(f"Heat-pump SPF: {annual['hp_spf']:.3f}")
    print(f"Total electricity: {annual['total_electric_kWh']:.1f} kWh")
    print(f"Total heat-pump exergy destruction: {annual['total_loss_kWh']:.1f} kWh")


if __name__ == "__main__":
    main()
