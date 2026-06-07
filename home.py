import os
import csv
import numpy as np

_script_dir = os.path.dirname(os.path.abspath(__file__))


class Home:
    """Represents a home/building for annual heating performance analysis."""


    def __init__(self, wall_area, materials, T_room, hp_power, COE,
                 window_thickness=0.04, WWR=0.2, pinch_difference_water=10,
                 pinch_difference_air=10,
                 ETACOMP=0.75, FPCOND=0.04, FPEVA=0.04,
                 refrigerant="R134a",
                 condenser_water_m_dot=0.25,
                 evaporator_air_m_dot=0.60):
        self.wall_area = wall_area
        self.materials = materials
        self.T_room = T_room
        self.hp_power = hp_power
        self.COE = COE
        self.window_thickness = window_thickness
        self._conductivity = self._load_conductivity()
        self.WWR = WWR
        self.Thot = T_room + pinch_difference_water
        self.pinch_difference_air = pinch_difference_air
        # Heat pump parameters for solv_realistic
        self.ETACOMP = ETACOMP
        self.FPCOND = FPCOND
        self.FPEVA = FPEVA
        self.refrigerant = refrigerant
        self.condenser_water_m_dot = condenser_water_m_dot
        self.evaporator_air_m_dot = evaporator_air_m_dot
        self.cp_water = 4180.0
        self.cp_air = 1006.0
        self._cycle = None  # lazy-initialized HeatPumpCycle

        

    def _load_conductivity(self):
        """Load thermal conductivity data from CSV."""
        csv_path = os.path.join(_script_dir, "construction_material.csv")
        conductivity = {}
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                name = row[0].strip()
                k = float(row[1])
                conductivity[name] = k
        return conductivity

    @property
    def R(self):
        """Overall thermal resistance of the building wall with window."""
        # Wall
        A_wall = self.wall_area * (1 - self.WWR)
        R_wall = 0.0
        for material, thickness in self.materials.items():
            k = self._conductivity[material]
            R_wall += thickness / (k * A_wall)

        # Window
        A_window = self.wall_area * self.WWR
        k_glass = self._conductivity["Window Glass (Float)"]
        R_window = self.window_thickness / (k_glass * A_window)

        R_total = 1.0 / (1.0 / R_wall + 1.0 / R_window)
        return R_total

    def heating_rate(self, T_out):
        """Calculate the heating rate (heat loss) at a given outdoor temperature."""
        return (self.T_room - T_out) / self.R

    @staticmethod
    def _sensible_stream_exergy_change(m_dot, cp, T_in, T_out, T0):
        """
        Rate of sensible-flow exergy change for an external fluid stream.

        The external air/water streams are approximated as constant-cp fluids
        with negligible pressure exergy:

            Delta B = m_dot cp [(T_out - T_in) - T0 ln(T_out / T_in)]
        """
        if m_dot <= 0 or cp <= 0 or T_in <= 0 or T_out <= 0 or T0 <= 0:
            return 0.0
        return m_dot * cp * ((T_out - T_in) - T0 * np.log(T_out / T_in))

    def _get_cop(self, Tcold):
        """
        Get the COP at a given cold-side refrigerant temperature
        using the realistic heat pump cycle model.

        Tcold : float
            Refrigerant temperature at the evaporator (cold side) in Kelvin.
        """
        if self._cycle is None:
            from cycle import HeatPumpCycle
            self._cycle = HeatPumpCycle(self.refrigerant)
        self._cycle.solv_realistic(Tcold, self.Thot,
                                   self.ETACOMP, self.FPCOND, self.FPEVA)
        return self._cycle.COP_internal()

    def calc_threshold_temp(self, T_low=200.0, T_high=None, tol=0.01):
        """
        Find the minimum outdoor air temperature the heat pump can support.

        Heat loss:  Q_loss = (T_room - T_out) / R
        Heat pump:  Q_hp   = COP(Tcold) * hp_power
                        Tcold = T_out - pinch_difference_air

        Solves for T_out where Q_hp = Q_loss via bisection.

        Returns the balance-point outdoor air temperature in Kelvin.
        """
        if T_high is None:
            T_high = self.T_room - 0.5

        R = self.R
        dT_air = self.pinch_difference_air

        def imbalance(T_out):
            """Positive when heat pump output exceeds heat loss."""
            Tcold = T_out - dT_air
            cop = self._get_cop(Tcold)
            return cop * self.hp_power - (self.T_room - T_out) / R

        # At T_high (near T_room), heat loss is tiny, COP is decent → > 0
        # At T_low (very cold), COP is poor, heat loss is large  → < 0
        f_low = imbalance(T_low)
        f_high = imbalance(T_high)

        if f_low > 0:
            # Even at T_low the heat pump can handle it — return T_low
            return T_low
        if f_high < 0:
            # Even near T_room the heat pump can't keep up — return T_room
            return self.T_room

        for _ in range(80):
            T_mid = (T_low + T_high) / 2.0
            if T_high - T_low < tol:
                break
            if imbalance(T_mid) > 0:
                T_high = T_mid
            else:
                T_low = T_mid
        self.T_crit = (T_low + T_high) / 2.0
        return (T_low + T_high) / 2.0


    def power_required(self, Tout):
        """
        Calculate the electrical power required at a given outdoor temperature.

        Tout : float
            Outdoor air temperature in Kelvin.

        Returns the electrical power required in Watts.
        """
        if Tout >= self.T_room:
            return 0.0

        R = self.R
        Q_loss = (self.T_room - Tout) / R  # heat loss rate (W)
        Tcold = Tout - self.pinch_difference_air
        cop = self._get_cop(Tcold)

        if Tout >= self.T_crit:
            # Heat pump alone can meet demand (modulates down)
            return Q_loss / cop
        else:
            # Heat pump at full power + electric resistance backup (COP=1)
            Q_hp = cop * self.hp_power
            return self.hp_power + (Q_loss - Q_hp)

    def annual_analysis(self, temperatures, dt_hours=0.5, T0="outdoor",
                        include_exergy=True, external_fluid_exergy=True):
        """
        Analyse annual heating performance for a weather temperature record.

        temperatures : np.ndarray
            Outdoor temperatures in degrees Celsius.
        dt_hours : float
            Time represented by each weather record.
        T0 : float or "outdoor"
            Dead-state temperature for exergy analysis in Kelvin. If "outdoor",
            each weather record uses its own outdoor temperature.
        include_exergy : bool
            If true, also accumulate component exergy destruction for the
            heat-pump cycle. Auxiliary resistance heating is not included in
            the heat-pump component exergy losses.
        external_fluid_exergy : bool
            If true, condenser and evaporator exergy destruction include the
            sensible exergy change of the water and air streams. If false,
            the previous thermal-reservoir approximation is used.

        Returns
        -------
        dict
            Annual totals and per-record arrays useful for Task 10/SPF plots.
        """
        from cycle import HeatPumpCycle

        temperatures = np.asarray(temperatures, dtype=float)
        dt_seconds = dt_hours * 3600.0
        components = ("compressor", "condenser", "throttle", "evaporator")
        component_loss = {name: 0.0 for name in components}
        external_exergy_change = {
            "condenser_water": 0.0,
            "evaporator_air": 0.0,
        }

        series = {
            "Tout_C": [],
            "heat_demand_W": [],
            "hp_heat_W": [],
            "backup_heat_W": [],
            "hp_electric_W": [],
            "backup_electric_W": [],
            "condenser_water_out_C": [],
            "evaporator_air_out_C": [],
            "cop": [],
            "mode": [],
        }
        totals = {
            "heat_demand_J": 0.0,
            "hp_heat_J": 0.0,
            "backup_heat_J": 0.0,
            "hp_electric_J": 0.0,
            "backup_electric_J": 0.0,
        }
        active_records = 0
        backup_records = 0
        inactive_records = 0
        skipped_records = 0
        external_limit_records = 0
        cycle = HeatPumpCycle(self.refrigerant) if include_exergy else None

        for T_celsius in temperatures:
            if not np.isfinite(T_celsius):
                skipped_records += 1
                continue

            Tout = T_celsius + 273.15
            values = {
                "Tout_C": T_celsius,
                "heat_demand_W": 0.0,
                "hp_heat_W": 0.0,
                "backup_heat_W": 0.0,
                "hp_electric_W": 0.0,
                "backup_electric_W": 0.0,
                "condenser_water_out_C": np.nan,
                "evaporator_air_out_C": np.nan,
                "cop": np.nan,
                "mode": "off",
            }

            if Tout >= self.T_room:
                inactive_records += 1
                for key, value in values.items():
                    series[key].append(value)
                continue

            Q_demand = self.heating_rate(Tout)
            if Q_demand <= 0:
                inactive_records += 1
                for key, value in values.items():
                    series[key].append(value)
                continue

            Tcold = Tout - self.pinch_difference_air
            if Tcold <= 0 or self.Thot <= 0 or Tout <= 0:
                skipped_records += 1
                continue

            try:
                if include_exergy:
                    cycle.solv_realistic(Tcold, self.Thot, self.ETACOMP,
                                         self.FPCOND, self.FPEVA)
                    q_out = cycle.h2 - cycle.h3
                    q_in = cycle.h1 - cycle.h4
                    w_in = cycle.h2 - cycle.h1
                    if q_out <= 0 or q_in <= 0 or w_in <= 0:
                        skipped_records += 1
                        continue
                    cop = q_out / w_in
                else:
                    cop = self._get_cop(Tcold)
                    q_out = q_in = None
            except Exception:
                skipped_records += 1
                continue

            hp_heat_capacity = cop * self.hp_power
            hp_heat = min(Q_demand, hp_heat_capacity)
            backup_heat = max(Q_demand - hp_heat, 0.0)
            hp_electric = hp_heat / cop
            backup_electric = backup_heat
            mode = "backup" if backup_heat > 0 else "hp_only"

            if backup_heat > 0:
                backup_records += 1
            active_records += 1

            totals["heat_demand_J"] += Q_demand * dt_seconds
            totals["hp_heat_J"] += hp_heat * dt_seconds
            totals["backup_heat_J"] += backup_heat * dt_seconds
            totals["hp_electric_J"] += hp_electric * dt_seconds
            totals["backup_electric_J"] += backup_electric * dt_seconds

            if include_exergy and hp_heat > 0:
                m_dot_ref = hp_heat / q_out
                dead_state = Tout if T0 == "outdoor" else float(T0)

                b1 = cycle.h1 - dead_state * cycle.s1
                b2 = cycle.h2 - dead_state * cycle.s2
                b3 = cycle.h3 - dead_state * cycle.s3
                b4 = cycle.h4 - dead_state * cycle.s4

                if external_fluid_exergy:
                    Q_cond = hp_heat
                    Q_evap = m_dot_ref * q_in

                    water_in = self.T_room
                    water_out = water_in + Q_cond / (
                        self.condenser_water_m_dot * self.cp_water
                    )
                    air_in = Tout
                    air_out = air_in - Q_evap / (
                        self.evaporator_air_m_dot * self.cp_air
                    )

                    if water_out >= self.Thot or air_out <= Tcold:
                        external_limit_records += 1

                    water_exergy_gain = self._sensible_stream_exergy_change(
                        self.condenser_water_m_dot, self.cp_water,
                        water_in, water_out, dead_state
                    )
                    air_exergy_gain = self._sensible_stream_exergy_change(
                        self.evaporator_air_m_dot, self.cp_air,
                        air_in, air_out, dead_state
                    )

                    external_exergy_change["condenser_water"] += (
                        water_exergy_gain * dt_seconds
                    )
                    external_exergy_change["evaporator_air"] += (
                        air_exergy_gain * dt_seconds
                    )

                    loss_rate = {
                        "compressor": m_dot_ref * (w_in - (b2 - b1)),
                        "condenser": m_dot_ref * (b2 - b3) - water_exergy_gain,
                        "throttle": m_dot_ref * (b3 - b4),
                        "evaporator": m_dot_ref * (b4 - b1) - air_exergy_gain,
                    }
                    values["condenser_water_out_C"] = water_out - 273.15
                    values["evaporator_air_out_C"] = air_out - 273.15
                else:
                    loss_rate = {
                        "compressor": m_dot_ref * dead_state * (
                            cycle.s2 - cycle.s1
                        ),
                        "condenser": m_dot_ref * dead_state * (
                            (cycle.s3 - cycle.s2) + q_out / self.T_room
                        ),
                        "throttle": m_dot_ref * dead_state * (
                            cycle.s4 - cycle.s3
                        ),
                        "evaporator": m_dot_ref * dead_state * (
                            (cycle.s1 - cycle.s4) - q_in / Tout
                        ),
                    }

                for component, loss in loss_rate.items():
                    component_loss[component] += max(loss, 0.0) * dt_seconds

            values.update({
                "heat_demand_W": Q_demand,
                "hp_heat_W": hp_heat,
                "backup_heat_W": backup_heat,
                "hp_electric_W": hp_electric,
                "backup_electric_W": backup_electric,
                "cop": cop,
                "mode": mode,
            })
            for key, value in values.items():
                series[key].append(value)

        total_electric_J = totals["hp_electric_J"] + totals["backup_electric_J"]
        hp_spf = (totals["hp_heat_J"] / totals["hp_electric_J"]
                  if totals["hp_electric_J"] > 0 else np.nan)
        system_spf = (totals["heat_demand_J"] / total_electric_J
                      if total_electric_J > 0 else np.nan)
        total_loss_J = sum(component_loss.values())

        result = {
            **totals,
            "total_electric_J": total_electric_J,
            "heat_demand_kWh": totals["heat_demand_J"] / 3.6e6,
            "hp_heat_kWh": totals["hp_heat_J"] / 3.6e6,
            "backup_heat_kWh": totals["backup_heat_J"] / 3.6e6,
            "hp_electric_kWh": totals["hp_electric_J"] / 3.6e6,
            "backup_electric_kWh": totals["backup_electric_J"] / 3.6e6,
            "total_electric_kWh": total_electric_J / 3.6e6,
            "operating_cost": total_electric_J / 3.6e6 * self.COE,
            "hp_spf": hp_spf,
            "system_spf": system_spf,
            "component_loss_J": component_loss,
            "component_loss_kWh": {
                key: value / 3.6e6 for key, value in component_loss.items()
            },
            "external_fluid_exergy": external_fluid_exergy,
            "external_fluid_exergy_change_J": external_exergy_change,
            "external_fluid_exergy_change_kWh": {
                key: value / 3.6e6
                for key, value in external_exergy_change.items()
            },
            "condenser_water_m_dot": self.condenser_water_m_dot,
            "evaporator_air_m_dot": self.evaporator_air_m_dot,
            "external_limit_records": external_limit_records,
            "total_loss_J": total_loss_J,
            "total_loss_kWh": total_loss_J / 3.6e6,
            "active_records": active_records,
            "backup_records": backup_records,
            "inactive_records": inactive_records,
            "records_skipped": skipped_records,
            "dt_hours": dt_hours,
            "series": {key: np.asarray(value) for key, value in series.items()},
        }
        self.annual_result = result
        return result

    def energy_required(self, temperatures, dt_hours=0.5):
        """
        Calculate total energy required for a year given temperature records.

        temperatures : np.ndarray
            Array of outdoor temperatures in degrees Celsius.
        dt_hours : float
            Time step between consecutive readings in hours (default 1 h).

        Returns
        -------
        total_energy : float
            Total electrical energy required in kWh.
        """
        return self.annual_analysis(
            temperatures, dt_hours=dt_hours, include_exergy=False
        )["total_electric_kWh"]

    def exergy_analysis(self, temperatures, dt_hours=0.5, T0="outdoor"):
        """
        Calculate annual component exergy destruction from weather records.

        temperatures : np.ndarray
            Array of outdoor temperatures in degrees Celsius, matching
            annual_performance.data_reader().
        dt_hours : float
            Time represented by each weather record in hours.
        T0 : float or "outdoor"
            Dead-state temperature in Kelvin. If "outdoor", each weather
            record is used as its own dead-state temperature.

        Returns
        -------
        dict
            Annual exergy destruction in J/kWh for compressor, condenser,
            throttle and evaporator, plus heat-pump duty summaries.
        """
        result = self.annual_analysis(temperatures, dt_hours=dt_hours, T0=T0,
                                      include_exergy=True)
        self.exergy_result = result
        return result
