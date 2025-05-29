import os
import json
import shutil
from typing import Optional
from constants import DEFAULT_COMBINED_ITEMS_FILE, MOUNTED_COMBINED_ITEMS_FILE
from utils.normalise import normalise_item_name

# Constants
COMBINED_TRACKED_ITEMS_FILE = MOUNTED_COMBINED_ITEMS_FILE
MAX_TRACKED_ITEMS = 20


def initialise_combined_tracked_file():
    """Ensure the combined tracked items file exists on the mounted volume."""
    if not os.path.exists(COMBINED_TRACKED_ITEMS_FILE):
        print("🆕 Mounted combined_tracked_items.json not found. Creating from default...")
        try:
            shutil.copyfile(DEFAULT_COMBINED_ITEMS_FILE, COMBINED_TRACKED_ITEMS_FILE)
            print("✅ Created combined_tracked_items.json on mounted drive from default.")
        except Exception as e:
            print(f"❌ Failed to copy default file to mounted location: {e}")
    else:
        print("✅ Mounted combined_tracked_items.json already exists.")


def load_combined_items_data():
    """Load data from the combined tracked items file."""
    try:
        with open(COMBINED_TRACKED_ITEMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ combined_tracked_items.json not found.")
        return {}


def save_combined_items_data(data: dict):
    """Save updated data to the combined tracked items file."""
    with open(COMBINED_TRACKED_ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def add_tracked_item(name: str, item_id: int, buy: Optional[int] = None, sell: Optional[int] = None):
    """Add a new item to tracking, optionally with buy/sell thresholds."""
    data = load_combined_items_data()
    normalised = normalise_item_name(name)

    if normalised in data:
        return False, "Item is already being tracked."
    if len(data) >= MAX_TRACKED_ITEMS:
        return False, "Cannot add more than 20 tracked items."

    data[normalised] = {"item_id": item_id}
    if buy is not None:
        data[normalised]["buy"] = buy
    if sell is not None:
        data[normalised]["sell"] = sell

    save_combined_items_data(data)
    return True, f"{name} (ID: {item_id}) added to tracking list."


def remove_tracked_item(name: str):
    """Remove an item from tracking."""
    data = load_combined_items_data()
    normalised = normalise_item_name(name)

    if normalised not in data:
        return False, "Item not found in tracked list."

    del data[normalised]
    save_combined_items_data(data)
    return True, f"{name} removed from tracking list."


def update_item_threshold(item_name: str, buy: Optional[int] = None, sell: Optional[int] = None):
    """Update thresholds for a tracked item."""
    data = load_combined_items_data()
    normalised = normalise_item_name(item_name)

    if normalised not in data:
        raise ValueError(f"Item '{item_name}' not found in combined items.")

    if buy is not None:
        data[normalised]["buy"] = buy
    if sell is not None:
        data[normalised]["sell"] = sell

    save_combined_items_data(data)


def get_pretty_name_by_id(item_id: int) -> str:
    """Get the display name of an item based on its Torn item ID."""
    data = load_combined_items_data()
    for pretty_name, info in data.items():
        if str(info.get("item_id")) == str(item_id):
            return pretty_name
    return str(item_id)


def list_tracked_items() -> dict:
    """Return a dict of tracked item names and their Torn IDs."""
    data = load_combined_items_data()
    return {pretty_name: info["item_id"] for pretty_name, info in data.items()}
