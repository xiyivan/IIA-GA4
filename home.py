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
                 refrigerant="R134a"):
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
        # Ensure T_crit is computed
        if not hasattr(self, 'T_crit'):
            self.calc_threshold_temp()

        total_energy_kwh = 0.0
        for T_celsius in temperatures:
            Tout = T_celsius + 273.15  # convert °C → K
            power_w = self.power_required(Tout)
            total_energy_kwh += power_w * dt_hours / 1000.0  # W·h → kWh

        return total_energy_kwh

    def exergy_analysis(self, temperatures, water_pinch=None, air_pinch=None,
                        water_flow_rate=None, air_flow_rate=None,
                        dt_hours=0.5, T0=298.15):
        """
        Calculate annual component exergy destruction from weather records.

        temperatures : np.ndarray
            Array of outdoor temperatures in degrees Celsius, matching
            annual_performance.data_reader().
        water_pinch, air_pinch : float, optional
            Temperature differences in K. If omitted, the values stored on the
            Home object are used.
        water_flow_rate, air_flow_rate : float, optional
            Kept for compatibility with the original unfinished interface. The
            annual model sizes refrigerant flow from the building heat demand.
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
        from cycle import HeatPumpCycle

        del water_flow_rate, air_flow_rate

        temperatures = np.asarray(temperatures, dtype=float)
        water_pinch = self.Thot - self.T_room if water_pinch is None else water_pinch
        air_pinch = self.pinch_difference_air if air_pinch is None else air_pinch
        dt_seconds = dt_hours * 3600.0

        cycle = HeatPumpCycle(self.refrigerant)
        component_loss = {
            "compressor": 0.0,
            "condenser": 0.0,
            "throttle": 0.0,
            "evaporator": 0.0,
        }
        total_heat_delivered = 0.0
        total_electric_work = 0.0
        active_records = 0
        inactive_records = 0
        skipped_records = 0
        operating_point_cache = {}

        for T_celsius in temperatures:
            if not np.isfinite(T_celsius):
                skipped_records += 1
                continue

            Tout = T_celsius + 273.15
            if Tout >= self.T_room:
                inactive_records += 1
                continue

            Q_demand = self.heating_rate(Tout)
            if Q_demand <= 0:
                inactive_records += 1
                continue

            Tcold = Tout - air_pinch
            Thot = self.T_room + water_pinch
            if Tcold <= 0 or Thot <= 0 or Tout <= 0:
                skipped_records += 1
                continue

            dead_state = Tout if T0 == "outdoor" else float(T0)
            cache_key = (round(Tcold, 6), round(Thot, 6), round(dead_state, 6))
            if cache_key in operating_point_cache:
                q_out, w_in, specific_loss = operating_point_cache[cache_key]
            else:
                try:
                    cycle.solv_realistic(Tcold, Thot, self.ETACOMP,
                                         self.FPCOND, self.FPEVA)
                except Exception:
                    skipped_records += 1
                    continue

                q_out = cycle.h2 - cycle.h3
                q_in = cycle.h1 - cycle.h4
                w_in = cycle.h2 - cycle.h1
                if q_out <= 0 or q_in <= 0 or w_in <= 0:
                    skipped_records += 1
                    continue

                specific_loss = {
                    "compressor": dead_state * (cycle.s2 - cycle.s1),
                    "condenser": dead_state * ((cycle.s3 - cycle.s2)
                                               + q_out / self.T_room),
                    "throttle": dead_state * (cycle.s4 - cycle.s3),
                    "evaporator": dead_state * ((cycle.s1 - cycle.s4)
                                                - q_in / Tout),
                }
                operating_point_cache[cache_key] = (q_out, w_in, specific_loss)

            cop = q_out / w_in
            hp_heat_capacity = cop * self.hp_power
            Q_from_hp = min(Q_demand, hp_heat_capacity)
            if Q_from_hp <= 0:
                inactive_records += 1
                continue

            m_dot_ref = Q_from_hp / q_out
            for component, loss_per_kg in specific_loss.items():
                component_loss[component] += max(loss_per_kg, 0.0) * m_dot_ref * dt_seconds

            total_heat_delivered += Q_from_hp * dt_seconds
            total_electric_work += m_dot_ref * w_in * dt_seconds
            active_records += 1

        total_loss = sum(component_loss.values())
        result = {
            "component_loss_J": component_loss,
            "total_loss_J": total_loss,
            "component_loss_kWh": {
                key: value / 3.6e6 for key, value in component_loss.items()
            },
            "total_loss_kWh": total_loss / 3.6e6,
            "heat_delivered_by_hp_J": total_heat_delivered,
            "heat_delivered_by_hp_kWh": total_heat_delivered / 3.6e6,
            "electric_work_to_hp_J": total_electric_work,
            "electric_work_to_hp_kWh": total_electric_work / 3.6e6,
            "active_records": active_records,
            "inactive_records": inactive_records,
            "records_skipped": skipped_records,
        }
        self.exergy_result = result
        return result
