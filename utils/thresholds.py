
import os
import discord
import json
from constants import THRESHOLDS_FILE
from utils.tracked_items import load_combined_items_data
from utils.normalise import normalise_item_name

# 🔄 Load just point thresholds (points.json stays separate)
def load_thresholds():
    try:
        with open(THRESHOLDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"buy": None, "sell": None}

def save_thresholds(thresholds):
    with open(THRESHOLDS_FILE, "w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=4)

# ✅ Post summary of all thresholds (points + items)
async def post_threshold_summary(bot):
    channel = discord.utils.get(bot.get_all_channels(), name="trading-alerts")
    if not channel:
        print("⚠️ 'trading-alerts' channel not found.")
        return

    point_thresholds = load_thresholds()
    combined_items = load_combined_items_data()

    message = "**Current Alert Thresholds**\n"

    if point_thresholds.get("buy") or point_thresholds.get("sell"):
        message += f"\n**Points:** Buy ≤ {point_thresholds.get('buy', 'N/A')} | Sell ≥ {point_thresholds.get('sell', 'N/A')}"

    for name, values in combined_items.items():
        buy = values.get("buy", "N/A")
        sell = values.get("sell", "N/A")
        message += f"\n**{name.title()}**: Buy ≤ {buy} | Sell ≥ {sell}"

    await channel.send(message)


