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
from utils.history import log_point_price, trim_item_price_history

POINTS_SILENT_CHECKS = 0

def start_loops(bot):
    check_point_market_loop.start(bot)
    check_item_prices_loop.start(bot)
    log_item_price_history_loop.start(bot)
    daily_trim_item_history_loop.start(bot)

@tasks.loop(minutes=1)
async def check_point_market_loop(bot):
    global POINTS_SILENT_CHECKS
    await bot.wait_until_ready()
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
                POINTS_SILENT_CHECKS = 0
            elif thresholds["sell"] and price >= thresholds["sell"]:
                await channel.send(f"🔥 **Points are expensive!** {price:n} T$ (≥ {thresholds['sell']})")
                POINTS_SILENT_CHECKS = 0
            else:
                POINTS_SILENT_CHECKS += 1
                if POINTS_SILENT_CHECKS >= 60:
                    await channel.send(f"🔍 **Points market check**: {price:n} T$ (no alerts triggered)")
                    POINTS_SILENT_CHECKS = 0

    except Exception as e:
        print(f"[Error checking point market] {e}")

@tasks.loop(seconds=20)
async def check_item_prices():
    await bot.wait_until_ready()
    global ITEM_SILENT_CHECKS

    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        return

    tracked_items = load_tracked_items()

    try:
        with open(ITEM_THRESHOLD_FILE, "r", encoding="utf-8") as f:
            thresholds = json.load(f)
    except FileNotFoundError:
        thresholds = {}

    channel = discord.utils.get(bot.get_all_channels(), name="trading-alerts")
    if not channel:
        print("⚠️ Channel 'trading-alerts' not found.")
        return

    alert_triggered = False

    for pretty_name, item_id in tracked_items.items():
        try:
            url = f"https://api.torn.com/v2/market/{item_id}/itemmarket?key={api_key}"
            response = requests.get(url)
            data = response.json()

            listings = data.get("itemmarket", {}).get("listings", [])
            if not listings:
                continue

            lowest_price = min(listing["price"] for listing in listings)
            log_item_price(item_id, lowest_price)

            item_threshold = thresholds.get(pretty_name.lower(), {})
            alert_msg = None

            if item_threshold.get("buy") and lowest_price <= item_threshold["buy"]:
                alert_msg = f"💰 **{pretty_name} is cheap!** {lowest_price:n} T$ (≤ {item_threshold['buy']})"
            elif item_threshold.get("sell") and lowest_price >= item_threshold["sell"]:
                alert_msg = f"🔥 **{pretty_name} is expensive!** {lowest_price:n} T$ (≥ {item_threshold['sell']})"

            if alert_msg:
                await channel.send(alert_msg)
                alert_triggered = True
                ITEM_SILENT_CHECKS = 0

        except Exception as e:
            print(f"[Error checking price for {pretty_name}] {e}")

    ITEM_SILENT_CHECKS += 1
    if ITEM_SILENT_CHECKS >= 180:  # 20 sec * 180 = 1 hour
        try:
            sample_item = next(iter(tracked_items))
            await channel.send(f"🔍 Item price check running — no alerts in the past hour (e.g., {sample_item}).")
            ITEM_SILENT_CHECKS = 0
        except StopIteration:
            pass

        
@tasks.loop(hours=24)
async def daily_trim_item_history_loop(bot):
    await bot.wait_until_ready()
    trim_item_price_history()
