# utils/trains_tracker.py

import os
import json
import requests

TORN_API_KEY = os.getenv("TORN_API_KEY")
TORN_LOG_URL = f"https://api.torn.com/user/?selections=log&key={TORN_API_KEY}"

TRAINS_FILE = "/mnt/data/train_tracker.json"

def initialise_train_file():
    if not os.path.exists(TRAINS_FILE):
        data = {
            "trains_bought": 0,
            "trains_received": 0,
            "cost_per_train": 0,
            "latest_log_timestamp": 0  # NEW: Track last log timestamp
        }
        with open(TRAINS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print("✅ Created train tracker JSON file.")


def load_train_data():
    initialise_train_file()
    with open(TRAINS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_train_data(data):
    with open(TRAINS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def update_received_trains_from_logs():
    """
    Checks Torn logs for new 'Company train receive' entries and updates trains_received.
    """
    train_data = load_train_data()
    last_ts = train_data.get("latest_log_timestamp", 0)

    # Fetch logs from Torn
    response = requests.get(TORN_LOG_URL)
    if response.status_code != 200:
        print("❌ Error fetching logs from Torn API.")
        return

    logs_data = response.json().get("log", {})
    new_train_logs = []

    for log_id, log_entry in logs_data.items():
        if log_entry.get("title") == "Company train receive":
            ts = log_entry.get("timestamp", 0)
            if ts > last_ts:
                new_train_logs.append(log_entry)
    
    if not new_train_logs:
        print("ℹ️ No new train logs found.")
        return
    
    new_trains = len(new_train_logs)
    train_data["trains_received"] += new_trains
    # Update the latest timestamp to the newest log
    newest_log = max(new_train_logs, key=lambda l: l["timestamp"])
    train_data["latest_log_timestamp"] = newest_log["timestamp"]
    
    save_train_data(train_data)
    print(f"✅ Added {new_trains} new train(s) from logs.")
