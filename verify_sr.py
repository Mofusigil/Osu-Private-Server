import sys
import time
from pathlib import Path
import os

# Add Star-Rating-Rebirth to path
# We assume we are running from bancho.py root
srr_path = Path.cwd() / "Star-Rating-Rebirth"
if srr_path.exists():
    sys.path.insert(0, str(srr_path))
else:
    print(f"SRR path {srr_path} not found.")

try:
    from algorithm import calculate
    print("Successfully imported calculate from algorithm.")
except ImportError as e:
    print(f"Failed to import algorithm: {e}")
    sys.exit(1)

# Map path
# Pick a map that exists
map_id = "1003821"
map_path = Path.cwd() / ".data/osu" / f"{map_id}.osu"

if not map_path.exists():
    # Try finding any .osu file
    data_path = Path.cwd() / ".data/osu"
    found = False
    if data_path.exists():
        for f in data_path.iterdir():
            if f.suffix == ".osu":
                map_path = f
                found = True
                break
    if not found:
        print(f"No .osu files found in {data_path}.")
        sys.exit(1)

print(f"Processing {map_path}...")
start_time = time.time()
try:
    sr = calculate(str(map_path), "NM")
    end_time = time.time()
    print(f"SR: {sr}")
    print(f"Time taken: {end_time - start_time:.4f} seconds")
except Exception as e:
    print(f"Error during calculation: {e}")
    import traceback
    traceback.print_exc()

# Run again to check cached speed
print("Running again (testing cache)...")
start_time = time.time()
try:
    sr = calculate(str(map_path), "NM")
    end_time = time.time()
    print(f"SR (2nd run): {sr}")
    print(f"Time taken (2nd run): {end_time - start_time:.4f} seconds")
except Exception as e:
    print(f"Error: {e}")
