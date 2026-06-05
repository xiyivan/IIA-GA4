"""One-time script: multiply Qc column (last column) in HP_26May2026_03.txt by 60."""

filepath = r"f:\OneDrive\Desktop\study\GA4\program\results\HP_26May2026_03.txt"

with open(filepath, "r") as f:
    lines = f.readlines()

with open(filepath, "w") as f:
    for line in lines:
        # Preserve header / comment / column-name lines as-is
        if line.startswith("#") or line.startswith(" ") is False:
            f.write(line)
            continue
        # Split on whitespace; tokens are fixed-width columns
        parts = line.rstrip("\n").split()
        if len(parts) < 12:
            f.write(line)
            continue
        # Multiply last column (Qc) by 60
        qc = float(parts[-1]) * 60
        # Rebuild line preserving original spacing:
        # find where the last column starts
        stripped = line.rstrip("\n")
        # Replace the last token while keeping leading spaces
        idx = stripped.rfind(parts[-1])
        new_tail = f"{qc:.4E}"
        new_line = stripped[:idx] + new_tail + "\n"
        f.write(new_line)

print("Done. Qc column multiplied by 60.")
