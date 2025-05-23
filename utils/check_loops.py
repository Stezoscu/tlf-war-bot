import os
import json
import time
import requests
from datetime import datetime
from discord.ext import tasks
import discord
from constants import (
    TRACKED_ITEMS,
    ITEM_IDS,
    ITEM_THRESHOLD_FILE,
    ITEM_HISTORY_FILE,
    POINT_HISTORY_FILE,
)
from utils.thresholds import load_thresholds, load_item_thresholds
from utils.history import log_point_price, log_item_price, trim_item_price_history



@tasks.loop(minutes=1)
async def check_point_market():
    await bot.wait_until_ready()

    global POINTS_SILENT_CHECKS
    alert_triggered = False

    thresholds = load_thresholds()
    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        return

    try:
        url = f"https://api.torn.com/market/?selections=pointsmarket&key={api_key}"
        response = requests.get(url)
        data = response.json()

        if "pointsmarket" not in data or not data["pointsmarket"]:
            print("[Error] No pointsmarket data found.")
            return

        lowest_offer = min(data["pointsmarket"].values(), key=lambda x: x["cost"])
        price = lowest_offer["cost"]
        log_point_price(price)


        channel = discord.utils.get(bot.get_all_channels(), name="trading-alerts")
        if channel:
            if thresholds["buy"] and price <= thresholds["buy"]:
                await channel.send(f"💰 **Points are cheap!** {price:n} T$ (≤ {thresholds['buy']})")
                alert_triggered = True
                POINTS_SILENT_CHECKS = 0
            elif thresholds["sell"] and price >= thresholds["sell"]:
                await channel.send(f"🔥 **Points are expensive!** {price:n} T$ (≥ {thresholds['sell']})")
                alert_triggered = True
                POINTS_SILENT_CHECKS = 0
            else:
                POINTS_SILENT_CHECKS += 1
                if POINTS_SILENT_CHECKS >= 60:
                    await channel.send(f"🔍 **Points market check**: {price:n} T$ (no alerts triggered)")
                    POINTS_SILENT_CHECKS = 0

    except Exception as e:
        print(f"[Error checking point market] {e}")

@tasks.loop(minutes=1)
async def check_item_prices():
    await bot.wait_until_ready()

    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        return

    try:
        with open(ITEM_THRESHOLD_FILE, "r", encoding="utf-8") as f:
            thresholds = json.load(f)
    except FileNotFoundError:
        thresholds = {}

    channel = discord.utils.get(bot.get_all_channels(), name="trading-alerts")
    if not channel:
        print("⚠️ Channel 'trading-alerts' not found.")
        return

    for pretty_name, clean_key in TRACKED_ITEMS.items():
        item_id = ITEM_IDS.get(clean_key)
        if not item_id:
            continue

        try:
            url = f"https://api.torn.com/v2/market/{item_id}/itemmarket?key={api_key}"
            response = requests.get(url)
            data = response.json()

            listings = data.get("itemmarket", {}).get("listings", [])
            if not listings:
                continue

            lowest_price = min(listing["price"] for listing in listings)
            item_threshold = thresholds.get(clean_key, {})
            alert_msg = None

            if item_threshold.get("buy") and lowest_price <= item_threshold["buy"]:
                alert_msg = f"💰 **{pretty_name} is cheap!** {lowest_price:n} T$ (≤ {item_threshold['buy']})"
            elif item_threshold.get("sell") and lowest_price >= item_threshold["sell"]:
                alert_msg = f"🔥 **{pretty_name} is expensive!** {lowest_price:n} T$ (≥ {item_threshold['sell']})"

            if alert_msg:
                await channel.send(alert_msg)

        except Exception as e:
            print(f"[Error checking price for {pretty_name}] {e}")




@tasks.loop(minutes=30)
async def log_item_price_history():
    await bot.wait_until_ready()

    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        return

    try:
        with open(ITEM_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = {}

    now = int(time.time())
    one_week_ago = now - 7 * 86400

    for pretty_name, clean_key in TRACKED_ITEMS.items():
        item_id = ITEM_IDS.get(clean_key)
        if not item_id:
            continue

        try:
            url = f"https://api.torn.com/v2/market/{item_id}/itemmarket?key={api_key}"
            response = requests.get(url)
            data = response.json()

            listings = data.get("itemmarket", {}).get("listings", [])
            if not listings:
                continue

            lowest_price = min(listing["price"] for listing in listings)

            if clean_key not in history:
                history[clean_key] = []

            history[clean_key].append({"timestamp": now, "price": lowest_price})

            # Trim to last 7 days
            history[clean_key] = [entry for entry in history[clean_key] if entry["timestamp"] >= one_week_ago]

        except Exception as e:
            print(f"[Error logging history for {pretty_name}] {e}")

    with open(ITEM_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


@tasks.loop(hours=24)
async def daily_trim_item_history():
    await bot.wait_until_ready()
    trim_item_price_history()

