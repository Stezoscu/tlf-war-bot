import json
import os

# Use persistent volume path
DATA_DIR = "/mnt/data"

def load_gear_perks():
    path = os.path.join(DATA_DIR, "gear_perks.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ gear_perks.json not found in /mnt/data. Gear perk commands will be disabled.")
        return {}
    except json.JSONDecodeError:
        print("❌ gear_perks.json is not valid JSON.")
        return {}

def load_job_perks():
    path = os.path.join(DATA_DIR, "job_perks_final.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ job_perks_final.json not found in /mnt/data. Job perk commands will be disabled.")
        return {}
    except json.JSONDecodeError:
        print("❌ job_perks_final.json is not valid JSON.")
        return {}

# Load these at import time so they're available as constants
GEAR_PERKS = load_gear_perks()
JOB_PERKS = load_job_perks()
