import aiohttp
import asyncio
import discord
from datetime import datetime
import os
import json

TORN_API_KEY = os.getenv("TORN_API_KEY")
ALERT_FILE_PATH = "/mnt/data/shoplifting_last_alerted.json"

last_alerted = set()
last_alert_time = None
first_run = True

# Create or load alert state
def load_alerted_shops():
    global last_alerted
    if os.path.exists(ALERT_FILE_PATH):
        with open(ALERT_FILE_PATH, "r") as f:
            try:
                last_alerted = set(json.load(f))
            except Exception as e:
                print(f"⚠️ Failed to load alert file: {e}")
                last_alerted = set()
    else:
        # Create file if missing
        with open(ALERT_FILE_PATH, "w") as f:
            json.dump([], f)

def save_alerted_shops():
    with open(ALERT_FILE_PATH, "w") as f:
        json.dump(list(last_alerted), f)

async def fetch_shoplifting_data():
    url = f"https://api.torn.com/torn/?selections=shoplifting&key={TORN_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

def get_vulnerable_shops(shop_data: dict):
    vulnerable = []
    for shop, security_list in shop_data.items():
        if security_list and all(s.get("disabled") for s in security_list):
            vulnerable.append(shop)
    return vulnerable

async def monitor_shoplifting(bot):
    global first_run, last_alert_time
    await bot.wait_until_ready()
    load_alerted_shops()

    channel = discord.utils.get(bot.get_all_channels(), name="shoplifting-alert")

    if first_run and channel:
        await channel.send("🟢 Shoplifting monitor is now online and checking every minute.")
        first_run = False

    while not bot.is_closed():
        try:
            now = datetime.utcnow()
            data = await fetch_shoplifting_data()
            shop_data = data.get("shoplifting", {})
            vulnerable = get_vulnerable_shops(shop_data)

            alert_sent = False

            for shop in vulnerable:
                if shop not in last_alerted:
                    last_alerted.add(shop)
                    alert_sent = True
                    last_alert_time = now
                    if channel:
                        name = shop.replace("_", " ").title()
                        await channel.send(f"🛒 **{name}** is fully vulnerable — all security disabled!")

            # Clean up alert cache
            last_alerted.intersection_update(vulnerable)
            save_alerted_shops()

            # Hourly heartbeat at HH:00
            if now.minute == 0 and now.second < 5:
                if not last_alert_time or (now - last_alert_time).seconds > 3600:
                    if channel:
                        await channel.send("🕐 Hourly check complete — no fully vulnerable shops found in the last hour.")

        except Exception as e:
            print(f"[Shoplifting Monitor] Error: {e}")

        await asyncio.sleep(60)
