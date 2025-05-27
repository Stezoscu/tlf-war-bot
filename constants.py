# constants.py
import os

# Torn API keys, mapped by use-case
API_KEYS = {
    "logs": os.getenv("TORN_API_KEY_S1"),
    "points": os.getenv("TORN_API_KEY_T1"),
    "items": os.getenv("TORN_API_KEY_B1"),
    "war": os.getenv("TORN_API_KEY_V1"),    
    "default": os.getenv("TORN_API_KEY")
}

GUILD_ID = 1344056482668478557
THRESHOLDS_FILE = "/mnt/data/point_thresholds.json"
POINT_HISTORY_FILE = "/mnt/data/point_price_history.json"
ITEM_ALERTS_FILE = "/mnt/data/item_price_alerts.json"
ITEM_HISTORY_FILE = "/mnt/data/item_price_history.json"
ITEM_THRESHOLD_FILE = "/mnt/data/item_thresholds.json"
POINTS_SILENT_CHECKS = 0

TRACKED_ITEMS = {
    "Erotic DVDs": "erotic_dvds",
    "Feathery Hotel Coupon": "feathery_hotel_coupon",
    "Xanax": "xanax",
    "Poison Mistletoe": "poison_mistletoe"
}

ITEM_IDS = {
    "xanax": "206",
    "erotic dvds": "366",
    "feathery hotel coupon": "367",
    "poison mistletoe": "865"
}

# from constants import API_KEYS

# api_key = API_KEYS["logs"]

def get_api_key(purpose: str) -> str:
    """Safely get an API key by purpose, or fall back to default."""
    return API_KEYS.get(purpose) or API_KEYS["default"]