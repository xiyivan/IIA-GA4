#!/usr/bin/env python3
"""Interactive CLI for heat pump data analysis. Run with: python cli.py"""

import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _script_dir)

from HP_plot import data

RESULTS_DIR = os.path.join(_script_dir, "results")


def _list_result_files():
    files = [f for f in os.listdir(RESULTS_DIR) if f.endswith(".txt")]
    return sorted(files)


def _print_properties(dataset):
    print(f"\nFile: {dataset.result_file_full_path}")
    print(f"Data points: {len(dataset.data.get('Time', []))}")
    print(f"\n{'Index':<6} {'Name':<10}")
    print("-" * 20)
    for i, name in enumerate(dataset.props):
        print(f"{i:<6} {name:<10}")
    print()


def _select_file():
    files = _list_result_files()
    print("\nAvailable result files:")
    for i, f in enumerate(files):
        print(f"  [{i}] {f}")

    choice = input(f"\nSelect file [default=0]: ").strip()
    idx = int(choice) if choice else 0
    return files[idx]


def _select_properties(dataset):
    _print_properties(dataset)
    print("Enter properties by index (e.g. 0 5 6) or name (e.g. Time T1r T2r)")
    raw = input("> ").strip()

    names = []
    for token in raw.split():
        try:
            idx = int(token)
            names.append(dataset.props[idx])
        except ValueError:
            names.append(token)  # assume it's a name, let dataset.plot fail if wrong
    return names



def _select_data_point(dataset):
    t = dataset.data["Time"]
    print(f"\nData range: {t[0]} – {t[-1]} s ({len(t)} points)")
    print("Enter timestamp (e.g. 266.54) or row index (e.g. idx=50):")
    raw = input("> ").strip()

    if raw.startswith("idx="):
        idx = int(raw.split("=")[1])
        timestamp = t[idx]
        print(f"Row {idx} (Time = {timestamp} s)")
    else:
        timestamp = float(raw)
        idx = dataset.find_time_index(t, timestamp)
        print(f"Closest: row {idx} (Time = {t[idx]} s)")
    return timestamp

def main():

    result_file = _select_file()
    dataset = data(result_file_name=result_file)
    print(f"\nLoaded: {result_file}")

    while True:
        print("[1] Plot")
        print("[2] Op")
        print("[3] Switch File")
        print("[q] Quit")
        choice = input("> ").strip().lower()

        if choice in ("q", "quit", "exit"):
            break
        elif choice == "1":
            names = _select_properties(dataset)
            if names:
                print(f"\nPlotting: {', '.join(names)}")
                save = input("Save to file? (no ext) or Enter to show: ").strip()
                dataset.plot(data_name_to_plot=names, file_name=save)
        elif choice == "2":
            dataset.get_op(_select_data_point(dataset))
        elif choice == "3":
            result_file = _select_file()
            dataset = data(result_file_name=result_file)
            print(f"\nLoaded: {result_file}")


if __name__ == "__main__":
    main()

