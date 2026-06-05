"""
One-off script: read task1-6.csv, for each valid record find the matching row
in the corresponding HP data file by timestamp (using bisect), and write a new
CSV with the original columns plus the extracted HP data columns.
"""
import csv
import bisect
import os
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
CSV_PATH = RESULTS_DIR / "task1-6.csv"
OUTPUT_PATH = RESULTS_DIR / "task1-6_extracted.csv"

# Column names from HP data files (taken from the comment header line)
HP_COLUMNS = [
    "Time (s)", "T1w (C)", "T2w (C)", "T1a (C)", "T2a (C)",
    "T1r (C)", "T2r (C)", "T3r (C)", "T4r (C)",
    "P1 (bar)", "P2 (bar)", "Ic (amp)", "Qc (l/min)",
]


def parse_timestamp(ts: str) -> float:
    """Convert 'MM:SS' or 'M:SS' timestamp to seconds."""
    ts = ts.strip()
    parts = ts.split(":")
    if len(parts) != 2:
        raise ValueError(f"Unexpected timestamp format: {ts!r}")
    minutes = int(parts[0])
    seconds = int(parts[1])
    return minutes * 60.0 + seconds


def load_hp_times(filepath: Path) -> list[float]:
    """Read the first (Time) column from an HP data file. Returns list of times in seconds."""
    times = []
    with open(filepath, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            line = line.strip()
            if not line:
                continue
            # First token is the time
            token = line.split()[0]
            times.append(float(token))
    return times


def load_hp_data_rows(filepath: Path) -> list[str]:
    """Read all data rows (as raw strings) from an HP data file, skipping headers."""
    rows = []
    with open(filepath, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            line = line.strip()
            if not line:
                continue
            rows.append(line)
    return rows


def find_closest_index(times: list[float], target: float) -> int:
    """Use bisect to find the index of the time value closest to target."""
    if not times:
        raise ValueError("Empty times list")
    idx = bisect.bisect_left(times, target)
    if idx == 0:
        return 0
    if idx == len(times):
        return len(times) - 1
    # Compare the two candidates on either side
    left_diff = target - times[idx - 1]
    right_diff = times[idx] - target
    return idx - 1 if left_diff <= right_diff else idx


def main():
    # 1. Read the input CSV
    records = []
    with open(CSV_PATH, "r", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)  # File, valve state(%), fan state(%), Time stamp, note
        for row in reader:
            records.append(row)

    # Trim trailing blank / empty rows
    while records and (len(records[-1]) == 0 or all(cell.strip() == "" for cell in records[-1])):
        records.pop()

    # 2. Build output header
    out_header = header + HP_COLUMNS

    # 3. Process each record
    out_rows = []
    for row in records:
        filename = row[0].strip()
        valve_state = row[1].strip()
        fan_state = row[2].strip()
        timestamp_str = row[3].strip()
        note = row[4].strip() if len(row) > 4 else ""

        # Skip invalid / placeholder rows
        if not filename:
            continue
        try:
            target_seconds = parse_timestamp(timestamp_str)
        except ValueError:
            print(f"Skipping row with bad timestamp: {row}")
            continue
        if not valve_state or not valve_state.isdigit():
            print(f"Skipping row with non-numeric valve state: {row}")
            continue
        if not fan_state or not fan_state.isdigit():
            print(f"Skipping row with non-numeric fan state: {row}")
            continue

        hp_file = RESULTS_DIR / f"{filename}.txt"
        if not hp_file.exists():
            print(f"File not found: {hp_file}, skipping row: {row}")
            continue

        # Load times and data rows
        times = load_hp_times(hp_file)
        data_rows = load_hp_data_rows(hp_file)

        # Find the closest row by timestamp
        idx = find_closest_index(times, target_seconds)
        matched_time = times[idx]
        matched_data = data_rows[idx]

        print(
            f"[{filename}] target={target_seconds:.0f}s → "
            f"closest idx={idx}, time={matched_time:.3f}s "
            f"(diff={abs(matched_time - target_seconds):.2f}s)"
        )

        # Build output row: original columns + HP data columns
        out_row = [filename, valve_state, fan_state, timestamp_str, note]
        # Parse the HP data row — split on whitespace
        hp_values = matched_data.split()
        out_row.extend(hp_values)
        out_rows.append(out_row)

    # 4. Write output CSV
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(out_header)
        writer.writerows(out_rows)

    print(f"\nDone. {len(out_rows)} records written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
