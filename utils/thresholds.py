# utils/thresholds.py

import os
import json
from constants import ITEM_THRESHOLD_FILE, TRACKED_ITEMS, THRESHOLDS_FILE

def load_item_thresholds():
    if not os.path.exists(ITEM_THRESHOLD_FILE):
        data = {value: {"buy": None, "sell": None} for value in TRACKED_ITEMS.values()}
        save_item_thresholds(data)
        return data

    with open(ITEM_THRESHOLD_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_item_thresholds(data):
    with open(ITEM_THRESHOLD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def normalise_item_name(name: str) -> str:
    for display_name, internal_key in TRACKED_ITEMS.items():
        if name.lower().strip() == display_name.lower() or name.lower().strip() == internal_key:
            return internal_key
    return None

def load_thresholds():
    try:
        with open(THRESHOLDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"buy": None, "sell": None}

def save_thresholds(thresholds):
    with open(THRESHOLDS_FILE, "w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=4)
