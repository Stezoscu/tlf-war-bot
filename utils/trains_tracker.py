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
            "latest_log_timestamp": 0
        }
        with open(TRAINS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print("✅ Created train tracker JSON file.")
    else:
        # Check if the structure is complete
        with open(TRAINS_FILE, "r+", encoding="utf-8") as f:
            existing_data = json.load(f)
            updated = False
            if "trains_bought" not in existing_data:
                existing_data["trains_bought"] = 0
                updated = True
            if "trains_received" not in existing_data:
                existing_data["trains_received"] = 0
                updated = True
            if "cost_per_train" not in existing_data:
                existing_data["cost_per_train"] = 0
                updated = True
            if "latest_log_timestamp" not in existing_data:
                existing_data["latest_log_timestamp"] = 0
                updated = True
            if updated:
                f.seek(0)
                json.dump(existing_data, f, indent=2)
                f.truncate()
                print("✅ Updated train tracker JSON file with missing fields.")

def load_train_data():
    initialise_train_file()
    with open(TRAINS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_train_data(data):
    with open(TRAINS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def set_train_data(trains_bought=None, trains_received=None, cost_per_train=None):
    data = load_train_data()
    if trains_bought is not None:
        data["trains_bought"] = trains_bought
    if trains_received is not None:
        data["trains_received"] = trains_received
    if cost_per_train is not None:
        data["cost_per_train"] = cost_per_train
    save_train_data(data)

def update_trains_received(count):
    data = load_train_data()
    data["trains_received"] += count
    save_train_data(data)

def update_received_trains_from_logs():
    data = load_train_data()
    last_ts = data.get("latest_log_timestamp", 0)

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
    data["trains_received"] += new_trains
    newest_log = max(new_train_logs, key=lambda l: l["timestamp"])
    data["latest_log_timestamp"] = newest_log["timestamp"]

    save_train_data(data)
    print(f"✅ Added {new_trains} new train(s) from logs.")
