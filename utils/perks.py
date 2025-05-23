import json

GEAR_PERKS_FILE = "/mnt/data/gear_perks.json"
JOB_PERKS_FILE = "/mnt/data/job_perks_final.json"

def load_gear_perks():
    try:
        with open(GEAR_PERKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ gear_perks.json not found.")
        return {}

def load_job_perks():
    try:
        with open(JOB_PERKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ job_perks_final.json not found.")
        return {}

# Load on import
gear_perks = load_gear_perks()
job_perks = load_job_perks()
