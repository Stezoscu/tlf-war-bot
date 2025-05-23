# utils/thresholds.py

import os
import discord
import json
from constants import ITEM_THRESHOLD_FILE, TRACKED_ITEMS, THRESHOLDS_FILE


async def post_threshold_summary(bot):
    channel = discord.utils.get(bot.get_all_channels(), name="trading-alerts")
    if not channel:
        print("⚠️ 'trading-alerts' channel not found.")
        return

    try:
        with open(ITEM_THRESHOLD_FILE, "r", encoding="utf-8") as f:
            item_thresholds = json.load(f)
    except FileNotFoundError:
        item_thresholds = {}

    point_thresholds = load_thresholds()

    message = "**Current Alert Thresholds**\n"

    if point_thresholds.get("buy") or point_thresholds.get("sell"):
        message += f"\n**Points:** Buy ≤ {point_thresholds.get('buy', 'N/A')} | Sell ≥ {point_thresholds.get('sell', 'N/A')}"

    for item_key, values in item_thresholds.items():
        pretty_name = next((k for k, v in TRACKED_ITEMS.items() if v == item_key), item_key)
        message += f"\n**{pretty_name}:** Buy ≤ {values.get('buy', 'N/A')} | Sell ≥ {values.get('sell', 'N/A')}"

    await channel.send(message)

def clean_item_thresholds():
    try:
        with open(ITEM_THRESHOLD_FILE, "r", encoding="utf-8") as f:
            thresholds = json.load(f)
    except FileNotFoundError:
        thresholds = {}

    valid_keys = set(TRACKED_ITEMS.values())
    cleaned = {k: v for k, v in thresholds.items() if k in valid_keys}

    if cleaned != thresholds:
        with open(ITEM_THRESHOLD_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=4)

        print("🧹 Cleaned invalid keys from item thresholds.")

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
