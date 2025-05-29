import os
import json
import time
import requests
from datetime import datetime
from discord.ext import tasks
import discord
from utils.tracked_items import load_combined_items_data
from constants import ITEM_HISTORY_FILE
from utils.thresholds import load_thresholds
from utils.history import log_point_price, trim_item_price_history

POINTS_SILENT_CHECKS = 0
ITEM_SILENT_CHECKS = 0

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
async def check_item_prices_loop(bot):
    await bot.wait_until_ready()
    global ITEM_SILENT_CHECKS

    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        return

    combined_data = load_combined_items_data()
    channel = discord.utils.get(bot.get_all_channels(), name="trading-alerts")
    if not channel:
        print("⚠️ Channel 'trading-alerts' not found.")
        return

    alert_triggered = False

    for name, info in combined_data.items():
        item_id = info.get("item_id")
        buy_threshold = info.get("buy")
        sell_threshold = info.get("sell")

        try:
            url = f"https://api.torn.com/v2/market/{item_id}/itemmarket?key={api_key}"
            response = requests.get(url)
            data = response.json()

            listings = data.get("itemmarket", {}).get("listings", [])
            if not listings:
                continue

            lowest_price = min(listing["price"] for listing in listings)

            alert_msg = None
            if buy_threshold and lowest_price <= buy_threshold:
                alert_msg = f"💰 **{name.title()} is cheap!** {lowest_price:n} T$ (≤ {buy_threshold})"
            elif sell_threshold and lowest_price >= sell_threshold:
                alert_msg = f"🔥 **{name.title()} is expensive!** {lowest_price:n} T$ (≥ {sell_threshold})"

            if alert_msg:
                await channel.send(alert_msg)
                alert_triggered = True
                ITEM_SILENT_CHECKS = 0

        except Exception as e:
            print(f"[Error checking price for {name.title()}] {e}")

    ITEM_SILENT_CHECKS += 1
    if ITEM_SILENT_CHECKS >= 180:
        try:
            sample_item = next(iter(combined_data))
            await channel.send(f"🔍 Item price check running — no alerts in the past hour (e.g., {sample_item.title()}).")
            ITEM_SILENT_CHECKS = 0
        except StopIteration:
            pass


@tasks.loop(minutes=30)
async def log_item_price_history(bot):
    await bot.wait_until_ready()

    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        return

    combined_data = load_combined_items_data()

    try:
        with open(ITEM_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = {}

    now = int(time.time())
    one_week_ago = now - 7 * 86400

    for name, info in combined_data.items():
        item_id = info.get("item_id")
        try:
            url = f"https://api.torn.com/v2/market/{item_id}/itemmarket?key={api_key}"
            response = requests.get(url)
            data = response.json()

            listings = data.get("itemmarket", {}).get("listings", [])
            if not listings:
                continue

            lowest_price = min(listing["price"] for listing in listings)

            normalised = name.lower()
            if normalised not in history:
                history[normalised] = []

            history[normalised].append({"timestamp": now, "price": lowest_price})

            # Trim to 7 days
            history[normalised] = [
                entry for entry in history[normalised] if entry["timestamp"] >= one_week_ago
            ]

        except Exception as e:
            print(f"[Error logging history for {name.title()}] {e}")

    with open(ITEM_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    print("[Log] Item price history updated.")


@tasks.loop(hours=24)
async def daily_trim_item_history_loop(bot):
    await bot.wait_until_ready()
    trim_item_price_history()


def start_loops(bot):
    check_point_market_loop.start(bot)
    check_item_prices_loop.start(bot)
    log_item_price_history.start(bot)
    daily_trim_item_history_loop.start(bot)
