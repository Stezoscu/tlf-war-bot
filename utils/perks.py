import json
import os

import shutil

def ensure_perks_data():
    gear_path = os.path.join(DATA_DIR, "gear_perks.json")
    job_path = os.path.join(DATA_DIR, "job_perks_final.json")

    if not os.path.exists(gear_path):
        try:
            shutil.copy("seed_data/gear_perks.json", gear_path)
            print("✅ Copied gear_perks.json to /mnt/data")
        except Exception as e:
            print(f"❌ Failed to copy gear_perks.json: {e}")

    if not os.path.exists(job_path):
        try:
            shutil.copy("seed_data/job_perks_final.json", job_path)
            print("✅ Copied job_perks_final.json to /mnt/data")
        except Exception as e:
            print(f"❌ Failed to copy job_perks_final.json: {e}")

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
ensure_perks_data()
GEAR_PERKS = load_gear_perks()
JOB_PERKS = load_job_perks()
