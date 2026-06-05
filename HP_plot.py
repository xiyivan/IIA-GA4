import os
import numpy as np
import matplotlib.pyplot as plt
import re
import bisect
from cycle import HeatPumpCycle


class data():
    def __init__(self, result_dir = None, result_file_name = "HP_15May2026_01.txt", output_dir = None):
        # Always resolve paths relative to this script's location, not the working directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if result_dir is None:
            result_dir = os.path.join(script_dir, "results")
        if output_dir is None:
            output_dir = os.path.join(script_dir, "results")

        self.result_file_full_path = os.path.join(result_dir, result_file_name)
        self.output_dir = output_dir

        self.read_data()

    def read_data(self):
        with open(self.result_file_full_path) as data_file:
            self.title = data_file.readline() # Read first header line
            propsline = data_file.readline() # Read second header line
            self.props = re.findall(r'(\w+)\s*\(', propsline)
            self.data = {name: [] for name in self.props}
            for line in data_file:
                vals = line.split() # Split each line into "words"
                if vals[0] != "#":
                    for i, name in enumerate(self.props):
                        self.data[name].append(eval(vals[i]))
    
    def plot(self, data_name_to_plot = ["Time"], file_name = ""):
        """
        plot the graph if no file name is given, save the graph if filename is given
        """
        for data_name in data_name_to_plot:
            plt.plot(self.data["Time"], self.data[data_name], label=data_name)
        plt.legend()
        if file_name == "":
            plt.show()
        else:
            plt.savefig(file_name + ".png")
    

    def find_time_index(self, time_list, time):
        idx = bisect.bisect_left(time_list, time)
        if idx < len(time_list) and time_list[idx] == time:
            return idx
        if idx == len(time_list):
            raise ValueError(f"value {time} over the list ")
        left_val = time_list[idx-1]
        right_val = time_list[idx]
        if abs(left_val - time) <= abs(right_val - time):
            return idx - 1
        else:
            return idx
            

    def get_op(self, timestamp):
        set_idx = self.find_time_index(self.data["Time"], timestamp)
        cycle = HeatPumpCycle()
        T1 = self.data["T1r"][set_idx] + 273.15
        T2 = self.data["T2r"][set_idx] + 273.15
        T3 = self.data["T3r"][set_idx] + 273.15
        T4 = self.data["T4r"][set_idx] + 273.15
        P1 = self.data["P1"][set_idx] * 1e5
        P2 = self.data["P2"][set_idx] * 1e5
        cycle.solve_exp(T1, T2, T3, T4, P1, P2, 0.05)
        PREF, TREF, CMPART, ETACOMP, FPCOND, FPEVA = cycle.get_operation_param()
        print(f"""
Reference point pressure: {PREF/1e5} bar
Reference point temperature: {TREF - 273.15} °C
Compressor pressure ratio: {CMPART}
Compressor isentropic efficiency: {ETACOMP*100} %
Fractional pressure loss in the condensor: {FPCOND*100} %
Fractional pressure loss in the evaporator: {FPEVA*100} %
""")
        # print("COP external" ,cycle.COP_external())
        print("COP internal" , cycle.COP_internal())
        

        

if __name__ == "__main__":
    data1 = data()
    # data1.plot(data_name_to_plot=["T1r", "T1w"])
    # data1.get_op(timestamp= 2.6654E+02)
    