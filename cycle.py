import CoolProp
import numpy as np
from matplotlib import pyplot as plt

class HeatPumpCycle():
    """
    INPUT
    T1, T2, T3, T4 — temperatures at stations 1–4
    P1, P2 — pressures at compressor inlet/outlet
    FPCOND — fractional pressure loss in condenser

    (2D array from solve(), shape (4,6))
    stations: 0=comp inlet, 1=comp outlet, 2=cond outlet, 3=evap inlet
    properties: [h, T, p, v, s, Q] (index 0–5)
    """
    def __init__(self, coolant_name = "R134a"):
        self.coolant_name = coolant_name
        self.coolant = CoolProp.AbstractState("HEOS", coolant_name)
        # key sequence h, T, p, v, s, Q
        self.keys = [CoolProp.iHmass, CoolProp.iT, CoolProp.iP, CoolProp.iDmass, CoolProp.iSmass, CoolProp.iQ]

    
    def plot_saturation(self):
        from CoolProp.CoolProp import PropsSI as si
        fluid = self.coolant_name

        pc = si(fluid, 'pcrit')
        pt = si(fluid, 'ptriple')

        p = np.geomspace(pt, pc, 500)

        ts = si('T', 'P', p, "Q", 0.0, fluid)
        sf = si('S', 'P', p, "Q", 0.0, fluid)
        sg = si('S', 'P', p, 'Q', 1.0, fluid)

        # vf = si('D', 'P', p, "Q", 0.0, fluid)
        # vg = si('D', 'P', p, 'Q', 1.0, fluid)

        T = np.concatenate((ts, np.flip(ts[1:])))
        s = np.concatenate((sf, np.flip(sg)[1:]))

        vf = 1.0 / si('D', 'P', p, "Q", 0.0, fluid)
        vg = 1.0 / si('D', 'P', p, 'Q', 1.0, fluid)
        v = np.concatenate((vf, np.flip(vg[1:])))
        p_plot = np.concatenate((p, np.flip(p[1:])))

        fig_ts, ax_ts = plt.subplots()
        ax_ts.plot(s, T, 'k-')
        ax_ts.set_xlabel('Specific entropy (kJ/kg K)')
        ax_ts.set_ylabel('Temperature (K)')
        ax_ts.set_title('Saturation Line for %s' % fluid)

        fig_pv, ax_pv = plt.subplots()
        ax_pv.plot(v, p_plot, 'k-')
        ax_pv.set_xlabel('Specific volume (m³/kg)')
        ax_pv.set_ylabel('Pressure (Pa)')
        ax_pv.set_title('Saturation Line (P-v) for %s' % fluid)

        return fig_ts, ax_ts, fig_pv, ax_pv

    def solv_realistic(self, TCOLD, THOT, ETACOMP, FPCOND, FPEVA, graph=False):
        if graph:
            fig_ts, ax_ts, fig_pv, ax_pv = self.plot_saturation()
        results = np.zeros((4,6))

        # station 1
        self.coolant.specify_phase(CoolProp.iphase_gas)
        self.coolant.update(CoolProp.QT_INPUTS, 1, TCOLD)
        results[0, :] = [self.coolant.keyed_output(k) for k in self.keys]
        P1 = results[0, 2]

        # station 3 (let T3 be THOT)
        self.coolant.unspecify_phase()
        self.coolant.update(CoolProp.QT_INPUTS, 0, THOT)
        results[2, :] = [self.coolant.keyed_output(k) for k in self.keys]
        P3 = results[2, 2]

        # station 2
        P2 = P3 / (1-FPCOND)
        s2s = results[0, 4]
        self.coolant.update(CoolProp.PSmass_INPUTS, P2, s2s)
        h2s = self.coolant.hmass()
        h2 = (h2s - results[0, 0])/ETACOMP + results[0,0]
        self.coolant.update(CoolProp.HmassP_INPUTS, h2, P2)
        results[1, :] = [self.coolant.keyed_output(k) for k in self.keys]


        # station 4: isoenthalpy expansion
        P4 = P1 / (1-FPEVA)
        h4 = results[2,0]
        self.coolant.update(CoolProp.HmassP_INPUTS, h4, P4)
        results[3, :] = [self.coolant.keyed_output(k) for k in self.keys]

        # Dry saturated vapour at P2 (inserted between station 2 and 3 for plotting)
        self.coolant.update(CoolProp.PQ_INPUTS, P2, 1.0)
        sat_vapor = np.array([self.coolant.keyed_output(k) for k in self.keys])


        if graph:
            results_full = np.insert(results, 2, sat_vapor.reshape(1, 6), axis=0)
            # T-s diagram
            plt.figure(fig_ts.number)
            plt.plot([results_full[j, 4] for j in (0, 1, 2, 3, 4, 0)],
                     [results_full[j, 1] for j in (0, 1, 2, 3, 4, 0)], 'o-')
            # P-v diagram (results[:,3] is density, convert to specific volume)
            plt.figure(fig_pv.number)
            v_vals = [1.0 / results_full[j, 3] for j in range(5)]
            plt.plot(v_vals + [v_vals[0]],
                     [results_full[j, 2] for j in (0, 1, 2, 3, 4, 0)], 'o-')
            v_min, v_max = min(v_vals), max(v_vals)
            margin = 0.01
            ax_pv.set_xlim(v_min - margin, v_max + margin)
            plt.show()

        self.results = results
        return results



    def solv_theory(self, PREF, TREF, CMPART, ETACOMP, FPCOND, FPEVA, graph=False):
        """
        pass input as a single value
        INPUT
        PREF
        TREF
        CMPART: compressor pressure ratio
        ETACOMP: isentropic efficiency of the compressor

        
        FPCOND: fraction pressure loss in the condensor
        FPEVA: fraction pressure loss in the evaporator

        properties: h, T, p, v, s, Q
                    0  1  2  3  4  5
        """
        if graph:
            fig_ts, ax_ts, fig_pv, ax_pv = self.plot_saturation()
        
        results = np.zeros((4,6))

        # station 1
        P1 = PREF
        T1 = TREF
        self.coolant.specify_phase(CoolProp.iphase_gas)
        self.coolant.update(CoolProp.PT_INPUTS, P1, T1)
        results[0, :] = [self.coolant.keyed_output(k) for k in self.keys]

        # station 2 : irreversible compressor
        P2 = P1 * CMPART
        s2s = results[0, 4]
        self.coolant.update(CoolProp.PSmass_INPUTS, P2, s2s)
        h2s = self.coolant.hmass()
        h2 = (h2s - results[0, 0])/ETACOMP + results[0,0]
        self.coolant.update(CoolProp.HmassP_INPUTS, h2, P2)
        results[1, :] = [self.coolant.keyed_output(k) for k in self.keys]

        # station 3: non-ideal condensor 
        self.coolant.unspecify_phase()
        P3 = P2 * (1-FPCOND)
        self.coolant.update(CoolProp.PQ_INPUTS, P3, 0.0)
        results[2, :] = [self.coolant.keyed_output(k) for k in self.keys]

        # station 4: isoenthalpy expansion
        P4 = P1 / (1-FPEVA)
        h4 = results[2,0]
        self.coolant.update(CoolProp.HmassP_INPUTS, h4, P4)
        results[3, :] = [self.coolant.keyed_output(k) for k in self.keys]

        # Dry saturated vapour at P2 (inserted between station 2 and 3 for plotting)
        self.coolant.update(CoolProp.PQ_INPUTS, P2, 1.0)
        sat_vapor = np.array([self.coolant.keyed_output(k) for k in self.keys])


        if graph:
            results_full = np.insert(results, 2, sat_vapor.reshape(1, 6), axis=0)
            # T-s diagram
            plt.figure(fig_ts.number)
            plt.plot([results_full[j, 4] for j in (0, 1, 2, 3, 4, 0)],
                     [results_full[j, 1] for j in (0, 1, 2, 3, 4, 0)], 'o-')
            # P-v diagram (results[:,3] is density, convert to specific volume)
            plt.figure(fig_pv.number)
            v_vals = [1.0 / results_full[j, 3] for j in range(5)]
            plt.plot(v_vals + [v_vals[0]],
                     [results_full[j, 2] for j in (0, 1, 2, 3, 4, 0)], 'o-')
            v_min, v_max = min(v_vals), max(v_vals)
            margin = 0.01
            ax_pv.set_xlim(v_min - margin, v_max + margin)
            plt.show()

        self.results = results
        return results
    

    def get_operation_param(self):
        """
        INPUT
        PREF
        TREF
        CMPART: compressor pressure ratio
        ETACOMP: isentropic efficiency of the compressor

        
        FPCOND: fraction pressure loss in the condensor
        FPEVA: fraction pressure loss in the evaporator
        properties: h, T, p, v, s, Q
                    0  1  2  3  4  5
        """
        PREF = self.results[0, 2]
        TREF = self.results[0, 1]

        CMPART = self.results[1,2]/self.results[0,2]
        
        # find ideal station 2 enthalpy
        self.coolant.update(CoolProp.PSmass_INPUTS, self.results[1, 2], self.results[0, 4])
        h2s = self.coolant.hmass()
        ETACOMP = (h2s - self.results[0, 0])/(self.results[1, 0] - self.results[0, 0])
        
        FPCOND = (self.results[1, 2] - self.results[2, 2])/self.results[1, 2]

        FPEVA = (self.results[3, 2] - self.results[0, 2])/self.results[3, 2]

        return PREF, TREF, CMPART, ETACOMP, FPCOND, FPEVA



    def solve_exp(self, T1, T2, T3, T4, P1, P2, FPCOND, graph=False):
        """Solve for a single operating point.
        return results[station, property]
        stations: 0=comp inlet, 1=comp outlet, 2=cond outlet, 3=evap inlet
        properties: h, T, p, v, s, Q
                    0  1  2  3  4  5
        """
        if graph:
            fig_ts, ax_ts, fig_pv, ax_pv = self.plot_saturation()

        results = np.zeros((4, 6))

        # station 1
        self.coolant.specify_phase(CoolProp.iphase_gas)
        self.coolant.update(CoolProp.PT_INPUTS, P1, T1)
        results[0, :] = [self.coolant.keyed_output(k) for k in self.keys]

        # station 2
        self.coolant.update(CoolProp.PT_INPUTS, P2, T2)
        results[1, :] = [self.coolant.keyed_output(k) for k in self.keys]
        self.coolant.unspecify_phase()

        # station 3: Pressure loss in the condensor

        P3 = P2 * (1 - FPCOND)
        self.coolant.update(CoolProp.PT_INPUTS, P3, T3)
        results[2, :] = [self.coolant.keyed_output(k) for k in self.keys]

        # Dry saturated vapour at P2 (inserted between station 2 and 3 for plotting)
        self.coolant.update(CoolProp.PQ_INPUTS, P2, 1.0)
        sat_vapor = np.array([self.coolant.keyed_output(k) for k in self.keys])

        # station 4: isoenthalpy expansion
        h4 = results[2, 0]

        self.coolant.update(CoolProp.QT_INPUTS, 0, T4)
        h4sf = self.coolant.hmass()
        self.coolant.update(CoolProp.QT_INPUTS, 1, T4)
        h4sg = self.coolant.hmass()

        Q4 = (h4 - h4sf) / (h4sg - h4sf)
        self.coolant.update(CoolProp.QT_INPUTS, Q4, T4)
        results[3, :] = [self.coolant.keyed_output(k) for k in self.keys]

        if graph:
            # Insert saturated vapour between station 2 (cond outlet) and station 3 (evap inlet)
            results_full = np.insert(results, 2, sat_vapor.reshape(1, 6), axis=0)
            # T-s diagram
            plt.figure(fig_ts.number)
            plt.plot([results_full[j, 4] for j in (0, 1, 2, 3, 4, 0)],
                     [results_full[j, 1] for j in (0, 1, 2, 3, 4, 0)], 'o-')
            # P-v diagram (results[:,3] is density, convert to specific volume)
            plt.figure(fig_pv.number)
            v_vals = [1.0 / results_full[j, 3] for j in range(5)]
            plt.plot(v_vals + [v_vals[0]],
                     [results_full[j, 2] for j in (0, 1, 2, 3, 4, 0)], 'o-')
            v_min, v_max = min(v_vals), max(v_vals)
            margin = 0.1 * (v_max - v_min) if v_max != v_min else 0.01
            ax_pv.set_xlim(v_min - margin, v_max + margin)
            plt.show()

        self.results = results
        return results

    def COP_internal(self):
        """Calculate COP from the last solve() results.
        Returns a scalar COP value."""
        Win = self.results[1, 0] - self.results[0, 0]
        Qout = self.results[1, 0] - self.results[2, 0]
        COP = Qout / Win
        return COP
    
    def COP_external(self, T1w, T2w, Ic, Qc):
        W = Ic * 230
        Q = (T2w-T1w) * Qc * 4184 / 60
        COP = Q/W
        return COP
    
    def Win(self):
        return self.results[1, 0] - self.results[0, 0]

    # Enthalpies
    @property
    def h1(self): return self.results[0, 0]
    @property
    def h2(self): return self.results[1, 0]
    @property
    def h3(self): return self.results[2, 0]
    @property
    def h4(self): return self.results[3, 0]

    # Entropies
    @property
    def s1(self): return self.results[0, 4]
    @property
    def s2(self): return self.results[1, 4]
    @property
    def s3(self): return self.results[2, 4]
    @property
    def s4(self): return self.results[3, 4]

    # Temperatures
    @property
    def T1(self): return self.results[0, 1]
    @property
    def T2(self): return self.results[1, 1]
    @property
    def T3(self): return self.results[2, 1]
    @property
    def T4(self): return self.results[3, 1]

    # Pressures
    @property
    def P1(self): return self.results[0, 2]
    @property
    def P2(self): return self.results[1, 2]
    @property
    def P3(self): return self.results[2, 2]
    @property
    def P4(self): return self.results[3, 2]

    

class ExergyAnalysis():

    
    def update_cycle(self, cycle):
        self.cycle = cycle
    
    def update_external(self, T1w, T2w, Qc, Ic, T1a, T2a):
        self.T1w = T1w
        self.T2w = T2w
        self.Qc = Qc
        self.Ic = Ic
        self.T1a = T1a
        self.T2a = T2a
    
    def __init__(self, cycle, T1w, T2w, Qc, Ic, T1a, T2a, T0):
        self.update_cycle(cycle)
        self.update_external(T1w, T2w, Qc, Ic, T1a, T2a)
        self.air = CoolProp.AbstractState("HEOS", "Air")
        self.air.specify_phase(CoolProp.iphase_gas)
        self.water = CoolProp.AbstractState("HEOS", "Water")
        self.water.specify_phase(CoolProp.iphase_liquid)
        self.T0 = T0

    def get_exergy(self, h, s):
        return h - self.T0*s

    def get_fluid_ratio(self):
        Patm = 1.015e5
        self.water.update(CoolProp.PT_INPUTS, Patm, self.T1w)
        self.h1w = self.water.hmass()
        self.s1w = self.water.smass()
        self.water.update(CoolProp.PT_INPUTS, Patm, self.T2w)
        self.h2w = self.water.hmass()
        self.s2w = self.water.smass()
        self.ratio_water_to_coolant = (self.cycle.h2-self.cycle.h3)/(self.h2w - self.h1w)

        self.air.update(CoolProp.PT_INPUTS, Patm, self.T1a)
        self.h1a = self.air.hmass()
        self.s1a = self.air.smass()
        self.air.update(CoolProp.PT_INPUTS, Patm, self.T2a)
        self.h2a = self.air.hmass()
        self.s2a = self.air.smass()
        self.ratio_air_to_coolant = (self.cycle.h1-self.cycle.h4)/(self.h1a-self.h2a)
    
    def solve_exergy_loss(self):
        """
        exergy distribution
        compressor, condenser, throttle, evaporator, water, air
        0           1           2           3       4       5
        """
        self.get_fluid_ratio()
        self.exergy_distribution = np.zeros((6))
        self.exergy_distribution[0] = self.get_exergy(self.cycle.h2, self.cycle.s2) - self.get_exergy(self.cycle.h1, self.cycle.s1)
        self.exergy_distribution[4] = self.ratio_water_to_coolant*(self.get_exergy(self.h1w, self.s1w) - self.get_exergy(self.h2w, self.s2w))
        self.exergy_distribution[1] = self.get_exergy(self.cycle.h3, self.cycle.s3) - self.get_exergy(self.cycle.h2, self.cycle.s2) - self.exergy_distribution[4]
        self.exergy_distribution[2] = self.get_exergy(self.cycle.h4, self.cycle.s4) - self.get_exergy(self.cycle.h3, self.cycle.s3)
        self.exergy_distribution[5] = self.ratio_air_to_coolant*(self.get_exergy(self.h1a, self.s1a) - self.get_exergy(self.h2a, self.s2a))
        self.exergy_distribution[3] = self.get_exergy(self.cycle.h1, self.cycle.s1) - self.get_exergy(self.cycle.h4, self.cycle.s4) - self.exergy_distribution[5]

    def plot_exergy(self):
        labels = ["Compressor", "Condenser\nloss", "Throttle", "Evaporator\nloss", "Water", "Air"]
        bars = plt.bar(labels, self.exergy_distribution)
        plt.ylabel("Exergy (J/kg)")
        plt.title("Exergy Distribution")
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        for bar in bars:
            h = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2, h, f"{h:.2e}",
                     ha="center", va="bottom" if h >= 0 else "top")
        plt.show()
        

