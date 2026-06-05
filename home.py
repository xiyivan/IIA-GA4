import os
import csv
import numpy as np

_script_dir = os.path.dirname(os.path.abspath(__file__))


class Home:
    """Represents a home/building for annual heating performance analysis."""


    def __init__(self, wall_area, materials, T_room, hp_power, COE,
                 window_thickness=0.004, WWR=0.2, pinch_difference_water=10,
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

    def energy_required(self, temperatures):
        """
        Calculate total energy required for a year given temperature records.

        temperatures : np.ndarray
            Array of outdoor temperatures (in Kelvin).
        """
        pass

    def exergy_analysis(self, water_pinch, air_pinch, water_flow_rate, air_flow_rate):
        """
        Calculate the amount of exergy through the year
        """
