import json
import time
import os
from datetime import datetime, timedelta
from constants import ITEM_HISTORY_FILE, TRACKED_ITEMS, POINT_HISTORY_FILE


def load_item_price_history():
    """Load historical price data for tracked items."""
    try:
        with open(ITEM_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print("❌ item_price_history.json is invalid.")
        return {}

def log_item_price(item_key, price):
    timestamp = int(time.time())

    try:
        with open(ITEM_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = {}

    if item_key not in history:
        history[item_key] = []

    history[item_key].append({"timestamp": timestamp, "price": price})

    # Prune to 7 days
    cutoff = timestamp - 7 * 86400
    history[item_key] = [entry for entry in history[item_key] if entry["timestamp"] >= cutoff]

    with open(ITEM_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def log_point_price(price):
    log_entry = {"timestamp": int(time.time()), "price": price}

    # Load existing history
    try:
        with open(POINT_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = []

    # Add new entry
    history.append(log_entry)

    # Prune entries older than 24h (86400 seconds)
    cutoff = int(time.time()) - 86400
    history = [entry for entry in history if entry["timestamp"] >= cutoff]

    with open(POINT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)



def trim_item_price_history(days_to_keep=7):
    try:
        with open(ITEM_HISTORY_FILE, "r", encoding="utf-8") as f:
            full_history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("[Trim] No valid history file found.")
        return

    cutoff = int((datetime.utcnow() - timedelta(days=days_to_keep)).timestamp())
    trimmed_history = {}

    for item, entries in full_history.items():
        trimmed = [entry for entry in entries if entry["timestamp"] >= cutoff]
        if trimmed:
            trimmed_history[item] = trimmed

    with open(ITEM_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed_history, f, indent=2)

    print("[Trim] Item price history trimmed to the last", days_to_keep, "days.")
