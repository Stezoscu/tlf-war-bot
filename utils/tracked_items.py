import os
import json

TRACKED_ITEMS_FILE = "/mnt/data/tracked_items.json"
MAX_TRACKED_ITEMS = 20

DEFAULT_TRACKED_ITEMS = {
    "xanax": "206",
    "erotic dvds": "366",
    "feathery hotel coupon": "367",
    "poison mistletoe": "865"
}

def ensure_tracked_items_file():
    if not os.path.exists(TRACKED_ITEMS_FILE):
        print("📦 tracked_items.json not found. Creating default version.")
        with open(TRACKED_ITEMS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_TRACKED_ITEMS, f, indent=2)

def load_tracked_items():
    ensure_tracked_items_file()
    with open(TRACKED_ITEMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tracked_items(items):
    with open(TRACKED_ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)

def add_tracked_item(name, item_id):
    items = load_tracked_items()
    if name in items:
        return False, "Item is already being tracked."
    if len(items) >= MAX_TRACKED_ITEMS:
        return False, "Cannot add more than 20 tracked items."
    items[name] = item_id
    save_tracked_items(items)
    return True, f"{name} (ID: {item_id}) added to tracking list."

def remove_tracked_item(name):
    items = load_tracked_items()
    if name not in items:
        return False, "Item not found in tracked list."
    del items[name]
    save_tracked_items(items)
    return True, f"{name} removed from tracking list."
