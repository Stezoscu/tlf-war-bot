import os
import json

TRAIN_FILE = "/mnt/data/company_trains.json"

def initialise_train_file():
    if not os.path.exists(TRAIN_FILE):
        print("🆕 Creating empty train tracker file...")
        data = {
            "trains_bought": 0,
            "trains_received": 0,
            "cost_per_train": 400000
        }
        with open(TRAIN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print("✅ Train tracker file created.")
    else:
        print("✅ Train tracker file already exists.")

def load_train_data():
    if not os.path.exists(TRAIN_FILE):
        return {
            "trains_bought": 0,
            "trains_received": 0,
            "cost_per_train": 400000
        }
    with open(TRAIN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_train_data(data):
    with open(TRAIN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def update_trains_received(count):
    data = load_train_data()
    data["trains_received"] += count
    save_train_data(data)

def set_train_data(trains_bought=None, trains_received=None, cost_per_train=None):
    data = load_train_data()
    if trains_bought is not None:
        data["trains_bought"] = trains_bought
    if trains_received is not None:
        data["trains_received"] = trains_received
    if cost_per_train is not None:
        data["cost_per_train"] = cost_per_train
    save_train_data(data)

def get_train_data():
    return load_train_data()
