import discord
from discord import app_commands
from discord.ext import commands
import os
import requests
import time
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import json
from datetime import datetime, timedelta
from pathlib import Path
from discord.ext import tasks
import asyncio

# GLOBALS
THRESHOLDS_FILE = "data/point_thresholds.json"
POINT_HISTORY_FILE = "data/point_price_history.json"
ITEM_ALERTS_FILE = "data/item_price_alerts.json"
ITEM_HISTORY_FILE = "data/item_price_history.json"
ITEM_THRESHOLD_FILE = "data/item_thresholds.json"
POINTS_SILENT_CHECKS = 0

TRACKED_ITEMS = {
    "Erotic DVDs": "erotic_dvds",
    "Feathery Hotel Coupon": "feathery_hotel_coupon",
    "Xanax": "xanax",
    "Poison Mistletoe": "poison_mistletoe"
}

ITEM_IDS = {
    "erotic_dvds": 38,
    "feathery_hotel_coupon": 206,
    "xanax": 224,
    "poison_mistletoe": 787
}



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


# Load or initialize thresholds
def load_thresholds():
    try:
        with open(THRESHOLDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"buy": None, "sell": None}

def save_thresholds(thresholds):
    with open(THRESHOLDS_FILE, "w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=4)

# Load gear perks from JSON
with open("data/gear_perks.json", "r", encoding="utf-8") as f:
    gear_perks = json.load(f)

# Load job perks from JSON
with open("data/job_perks_final.json", "r", encoding="utf-8") as f:
    job_perks = json.load(f)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def load_item_thresholds():
    if not os.path.exists(ITEM_THRESHOLD_FILE):
        data = {key: {"buy": None, "sell": None} for key in TRACKED_ITEMS.values()}
        save_item_thresholds(data)
        return data

    with open(ITEM_THRESHOLD_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_item_thresholds(data):
    with open(ITEM_THRESHOLD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def log_item_price(item_key, price):
    timestamp = int(time.time())

    # Load existing history
    try:
        with open(ITEM_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = {}

    if item_key not in history:
        history[item_key] = []

    # Add entry
    history[item_key].append({"timestamp": timestamp, "price": price})

    # Prune older than 7 days
    cutoff = timestamp - 7 * 86400
    history[item_key] = [entry for entry in history[item_key] if entry["timestamp"] >= cutoff]

    with open(ITEM_HISTORY_FILE, "w", encoding="utf-8") as f:
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

# ---- Prediction logic ----
def predict_war_end(current_hour, current_lead, your_score, starting_score_goal):
    lead_gain_per_hour = current_lead / current_hour
    opponent_score = your_score - current_lead

    hours = np.arange(current_hour, 200, 0.5)
    lead_values = current_lead + lead_gain_per_hour * (hours - current_hour)
    target_values = starting_score_goal * (0.99) ** (hours - 24)

    end_index = np.argmax(lead_values >= target_values)
    end_hour = hours[end_index]
    final_lead = lead_values[end_index]

    opponent_gain_per_hour = (opponent_score + (lead_gain_per_hour * current_hour)) / current_hour - lead_gain_per_hour
    hours_remaining = end_hour - current_hour
    estimated_opponent_final = opponent_score + opponent_gain_per_hour * hours_remaining
    estimated_your_final = estimated_opponent_final + final_lead

    return {
        "war_end_hour": round(end_hour, 1),
        "hours_remaining": round(hours_remaining, 1),
        "your_final_score": int(estimated_your_final),
        "opponent_final_score": int(estimated_opponent_final),
        "final_lead": int(final_lead)
    }

# ---- Torn API fetcher ----
def fetch_v2_war_data():
    api_key = os.getenv("TORN_API_KEY")
    your_faction_id = int(os.getenv("FACTION_ID"))

    url = f"https://api.torn.com/v2/faction/?selections=wars&key={api_key}"
    response = requests.get(url)
    data = response.json()

    ranked_war = data.get("wars", {}).get("ranked")
    if not ranked_war:
        raise ValueError("No ranked war found")

    factions = ranked_war["factions"]
    if len(factions) != 2:
        raise ValueError("Expected exactly 2 factions in war data")

    if factions[0]["id"] == your_faction_id:
        your = factions[0]
        enemy = factions[1]
    else:
        your = factions[1]
        enemy = factions[0]

    start_timestamp = ranked_war["start"]
    current_timestamp = time.time()
    current_hour = round((current_timestamp - start_timestamp) / 3600, 1)

    your_score = your["score"]
    enemy_score = enemy["score"]
    current_lead = your_score - enemy_score
    starting_goal = ranked_war.get("target", 3000)

    return {
        "war_id": ranked_war["war_id"],
        "factions": [your["name"], enemy["name"]],
        "start": start_timestamp,
        "current_hour": current_hour,
        "your_score": your_score,
        "current_lead": current_lead,
        "starting_goal": starting_goal
    }

# ---- Logging helper ----
def log_war_data(data: dict, result: dict):
    log_path = Path("data/current_war.json")
    timestamp = int(datetime.utcnow().timestamp())

    log_entry = {
        "timestamp": timestamp,
        "current_hour": data["current_hour"],
        "your_score": data["your_score"],
        "lead": data["current_lead"],
        "target": data["starting_goal"],
        "predicted_end": result["war_end_hour"]
    }

    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if existing["war_id"] != data["war_id"]:
            # New war, reset log
            log_data = {
                "war_id": data["war_id"],
                "factions": data["factions"],
                "start": data["start"],
                "history": [log_entry]
            }
        else:
            existing["history"].append(log_entry)
            log_data = existing
    else:
        # New file
        log_data = {
            "war_id": data["war_id"],
            "factions": data["factions"],
            "start": data["start"],
            "history": [log_entry]
        }

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=4)

# ---- Manual command ----
@bot.tree.command(name="warpredict", description="Manually predict Torn war end.")
@app_commands.describe(
    current_hour="How many hours has the war been running?",
    current_lead="Your current lead (your score - enemy score)",
    your_score="Your faction's score",
    starting_goal="Starting lead target (e.g., 3000)"
)
async def warpredict(interaction: discord.Interaction, current_hour: float, current_lead: int, your_score: int, starting_goal: int):
    result = predict_war_end(current_hour, current_lead, your_score, starting_goal)

    # Create pseudo-data for logging
    pseudo_data = {
        "war_id": 0,
        "factions": ["Manual Input", "Manual Input"],
        "start": int(time.time()) - int(current_hour * 3600),
        "current_hour": current_hour,
        "your_score": your_score,
        "current_lead": current_lead,
        "starting_goal": starting_goal
    }
    log_war_data(pseudo_data, result)

    await interaction.response.send_message(
        f"🧠 **TLF Torn War Predictor**\n"
        f"📅 War ends at hour **{result['war_end_hour']}** (in {result['hours_remaining']}h)\n"
        f"🏁 Final Scores:\n"
        f" - You: **{result['your_final_score']}**\n"
        f" - Opponent: **{result['opponent_final_score']}**\n"
        f"📊 Final Lead: **{result['final_lead']}**"
    )

# ---- Auto command from Torn API ----
@bot.tree.command(name="autopredict", description="Automatically predict war end using live Torn API data.")
@app_commands.describe(starting_goal="Optional: enter the original target (default is 3000)")
async def autopredict(interaction: discord.Interaction, starting_goal: int = 3000):
    try:
        data = fetch_v2_war_data()
        data["starting_goal"] = starting_goal

        result = predict_war_end(
            data["current_hour"],
            data["current_lead"],
            data["your_score"],
            data["starting_goal"]
        )

        log_war_data(data, result)

        current_target = data["starting_goal"] * (0.99) ** (data["current_hour"] - 24)
        current_target = round(current_target, 1)

        hours = np.arange(data["current_hour"], result["war_end_hour"] + 1, 0.5)
        lead_gain_per_hour = data["current_lead"] / data["current_hour"]
        lead_values = data["current_lead"] + lead_gain_per_hour * (hours - data["current_hour"])
        target_values = data["starting_goal"] * (0.99) ** (hours - 24)

        fig, ax = plt.subplots()
        ax.plot(hours, lead_values, label="Your Lead")
        ax.plot(hours, target_values, label="Target", linestyle="--")
        ax.axvline(result["war_end_hour"], color="red", linestyle=":", label="Predicted End")
        ax.set_title("Lead vs. Decaying Target")
        ax.set_xlabel("War Hour")
        ax.set_ylabel("Points")
        ax.legend()
        ax.grid(True)

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        file = discord.File(fp=buf, filename="prediction_chart.png")
        plt.close()

        await interaction.response.send_message(
            content=(
                f"📡 **Auto Prediction Based on Live Torn Data**\n"
                f"🕓 War Duration: **{data['current_hour']} hours**\n"
                f"📊 Current Score: **{data['your_score']}** | Lead: **{data['current_lead']}**\n"
                f"🎯 Starting Target: **{data['starting_goal']}**\n"
                f"📉 **Predicted Target Right Now**: **{current_target}**\n"
                f"📅 Predicted End: **hour {result['war_end_hour']}** (in {result['hours_remaining']}h)\n"
                f"🏁 Final Score Estimate:\n"
                f" - You: **{result['your_final_score']}**\n"
                f" - Opponent: **{result['opponent_final_score']}**"
            ),
            file=file
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}")

# (Gear/job perk commands continue unchanged...)
# ---- Gear perk commands ----
@bot.tree.command(name="check_gear_perk", description="Look up a gear perk and get its description.")
@app_commands.describe(perk_name="Name of the gear perk to look up")
async def check_gear_perk(interaction: discord.Interaction, perk_name: str):
    perk = next((name for name in gear_perks if name.lower() == perk_name.lower()), None)
    if perk:
        await interaction.response.send_message(f"🔍 **{perk}**: {gear_perks[perk]}")
    else:
        await interaction.response.send_message(f"❌ Perk '{perk_name}' not found.")

@bot.tree.command(name="list_gear_perks", description="List all gear perks.")
async def list_gear_perks(interaction: discord.Interaction):
    perk_list = "\n".join(sorted(gear_perks.keys()))
    await interaction.response.send_message(f"📜 **Gear Perks List**:\n```{perk_list}```")

# ---- Job perk commands ----
@bot.tree.command(name="check_job_perk", description="Look up perks for a specific job.")
@app_commands.describe(job_name="Name of the job (as in /list_jobs)")
async def check_job_perk(interaction: discord.Interaction, job_name: str):
    matched_job = next((j for j in job_perks if j.lower() == job_name.lower()), None)
    if not matched_job:
        await interaction.response.send_message(f"❌ Job '{job_name}' not found. Try /list_jobs for valid names.")
        return

    perks = job_perks[matched_job]
    response = f"🧾 **Perks for {matched_job}:**\n"
    for perk in perks:
        response += f"• **{perk['name']}** – {perk['effect']}\n"
    await interaction.response.send_message(response)

@bot.tree.command(name="list_jobs", description="Show all jobs with perks available.")
async def list_jobs(interaction: discord.Interaction):
    job_list = "\n".join(sorted(job_perks.keys()))
    await interaction.response.send_message(f"📋 **Available Jobs:**\n```{job_list}```")

@bot.tree.command(name="list_job_perks", description="List all job perks in a thread.")
async def list_job_perks(interaction: discord.Interaction):
    await interaction.response.send_message("📖 Sending all job perks in a thread...")

    thread = await interaction.channel.create_thread(
        name="📚 Job Perks Reference",
        type=discord.ChannelType.public_thread,
        message=interaction.original_response()
    )

    for job, perks in job_perks.items():
        perk_lines = [f"**{perk['name']}** – {perk['effect']}" for perk in perks]
        msg = f"**{job}**\n" + "\n".join(perk_lines)
        await thread.send(msg)

@bot.tree.command(name="set_points_buy", description="Set alert if point price goes below this value")
@app_commands.describe(price="Alert if point price drops below this amount")
async def set_points_buy(interaction: discord.Interaction, price: int):
    thresholds = load_thresholds()
    thresholds["buy"] = price
    save_thresholds(thresholds)
    await interaction.response.send_message(f"✅ Buy alert set: notify if points fall below **{price:n}** T$", ephemeral=True)

@bot.tree.command(name="set_points_sell", description="Set alert if point price goes above this value")
@app_commands.describe(price="Alert if point price rises above this amount")
async def set_points_sell(interaction: discord.Interaction, price: int):
    thresholds = load_thresholds()
    thresholds["sell"] = price
    save_thresholds(thresholds)
    await interaction.response.send_message(f"✅ Sell alert set: notify if points rise above **{price:n}** T$", ephemeral=True)

@bot.tree.command(name="check_points_price", description="Check the current market price of points")
async def check_points_price(interaction: discord.Interaction):
    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        await interaction.response.send_message("❌ Torn API key not set.")
        return

    try:
        url = f"https://api.torn.com/market/?selections=pointsmarket&key={api_key}"
        response = requests.get(url)
        data = response.json()

        if "pointsmarket" not in data or not data["pointsmarket"]:
            await interaction.response.send_message("❌ No points data found.")
            return

        lowest_offer = min(data["pointsmarket"].values(), key=lambda x: x["cost"])
        price = lowest_offer["cost"]
        quantity = lowest_offer["quantity"]

        await interaction.response.send_message(
            f"📈 **Current Lowest Point Price:** {price:n} T$ per point\n📦 Quantity Available: {quantity}"
        )

    except Exception as e:
        await interaction.response.send_message(f"❌ Error fetching price: {e}")


@bot.tree.command(name="set_item_sell_price", description="Set high alert sell price for an item")
@app_commands.describe(item="Name of the item (e.g., Xanax)", price="Price to trigger alert if exceeded")
async def set_item_sell_price(interaction: discord.Interaction, item: str, price: int):
    thresholds = load_item_thresholds()
    item_lower = item.lower()

    if item_lower not in thresholds:
        thresholds[item_lower] = {"buy": None, "sell": price}
    else:
        thresholds[item_lower]["sell"] = price

    save_item_thresholds(thresholds)
    await interaction.response.send_message(f"📈 Set **sell** alert for **{item}** at **{price:n}** T$", ephemeral=True)

@bot.tree.command(name="set_item_buy_price", description="Set low alert buy price for an item")
@app_commands.describe(item="Name of the item (e.g., Xanax)", price="Price to trigger alert if dropped below")
async def set_item_buy_price(interaction: discord.Interaction, item: str, price: int):
    thresholds = load_item_thresholds()
    item_lower = item.lower()

    if item_lower not in thresholds:
        thresholds[item_lower] = {"buy": price, "sell": None}
    else:
        thresholds[item_lower]["buy"] = price

    save_item_thresholds(thresholds)
    await interaction.response.send_message(f"📉 Set **buy** alert for **{item}** at **{price:n}** T$", ephemeral=True)

@bot.tree.command(name="check_item_price", description="Check the current lowest market price of an item")
@app_commands.describe(item="Name of the item (e.g., Xanax)")
async def check_item_price(interaction: discord.Interaction, item: str):
    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        await interaction.response.send_message("❌ Torn API key not set.")
        return

    item_name = item.lower()
    
    if item_name not in ITEM_IDS:
        await interaction.response.send_message(f"❌ Item '{item}' not supported. Try: erotic_dvds, feathery_hotel_coupon, xanax, poison_mistletoe")
        return
    item_id = ITEM_IDS[item_name]

    if item_name not in ITEM_IDS:
        await interaction.response.send_message(f"❌ Item '{item}' not supported. Try: {', '.join(item_ids.keys())}")
        return

    item_id = ITEM_IDS[item_name]
    try:
        url = f"https://api.torn.com/market/{item_id}?key={api_key}"
        response = requests.get(url)
        data = response.json()

        lowest = data["bazaar"][0] if data.get("bazaar") else None
        if not lowest:
            await interaction.response.send_message(f"❌ No bazaar listings found for **{item}**.")
            return

        price = int(lowest["cost"])
        quantity = lowest.get("quantity", "N/A")
        seller = lowest.get("ID", "Unknown")

        await interaction.response.send_message(
            f"🔎 **{item.title()}** lowest price: **{price:n}** T$ for {quantity} units (Seller ID: {seller})"
        )

    except Exception as e:
        await interaction.response.send_message(f"❌ Error fetching item price: {e}")

@bot.tree.command(name="item_price_graph", description="Show a price trend graph for a tracked item over the last week")
@app_commands.describe(item="Tracked item name (e.g., Xanax, Erotic DVDs)")
async def item_price_graph(interaction: discord.Interaction, item: str):
    await interaction.response.defer()

    item = item.lower()
    file_path = "data/item_price_history.json"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        await interaction.followup.send("❌ No price history data found.")
        return

    if item not in history or not history[item]:
        await interaction.followup.send(f"❌ No data found for **{item.title()}**.")
        return

    entries = history[item]
    times = [datetime.utcfromtimestamp(e["timestamp"]).strftime("%d %b %H:%M") for e in entries]
    prices = [e["price"] for e in entries]

    fig, ax = plt.subplots()
    ax.plot(times, prices, marker="o", linestyle="-", label=item.title())
    ax.set_title(f"{item.title()} Price Trend (Last 7 Days)")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Price (T$)")
    plt.xticks(rotation=45)
    ax.grid(True)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    file = discord.File(buf, filename="item_trend.png")
    plt.close()

    await interaction.followup.send(file=file)




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

    thresholds_path = "data/item_thresholds.json"
    try:
        with open(thresholds_path, "r", encoding="utf-8") as f:
            thresholds = json.load(f)
    except FileNotFoundError:
        thresholds = {}

    item_ids = {
        "xanax": "258",
        "erotic dvds": "264",
        "feathery hotel coupon": "269",
        "poison mistletoe": "2067"
    }

    channel = discord.utils.get(bot.get_all_channels(), name="trading-alerts")
    if not channel:
        print("⚠️ Channel 'trading-alerts' not found.")
        return

    for name, item_id in item_ids.items():
        try:
            url = f"https://api.torn.com/market/{item_id}?key={api_key}"
            response = requests.get(url)
            data = response.json()

            if "bazaar" not in data or not data["bazaar"]:
                continue

            lowest = data["bazaar"][0]
            price = int(lowest["cost"])

            # Alert logic
            item_threshold = thresholds.get(name, {})
            alert_msg = None

            if item_threshold.get("buy") and price <= item_threshold["buy"]:
                alert_msg = f"💰 **{name.title()} is cheap!** {price:n} T$ (≤ {item_threshold['buy']})"

            elif item_threshold.get("sell") and price >= item_threshold["sell"]:
                alert_msg = f"🔥 **{name.title()} is expensive!** {price:n} T$ (≥ {item_threshold['sell']})"

            if alert_msg:
                await channel.send(alert_msg)

        except Exception as e:
            print(f"[Error checking price for {name}] {e}")


@tasks.loop(hours=12)
async def post_hourly_point_graph():
    await bot.wait_until_ready()

    try:
        with open(POINT_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)

        if len(history) < 2:
            return  # Not enough data

        times = [datetime.utcfromtimestamp(e["timestamp"]).strftime("%H:%M") for e in history]
        prices = [e["price"] for e in history]

        fig, ax = plt.subplots()
        ax.plot(times, prices, label="Point Price")
        ax.set_title("Point Price - Last 24 Hours")
        ax.set_xlabel("Time (UTC)")
        ax.set_ylabel("Price (T$)")
        ax.grid(True)
        plt.xticks(rotation=45)

        buf = BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        buf.seek(0)
        file = discord.File(buf, filename="points_graph.png")
        plt.close()

        channel = discord.utils.get(bot.get_all_channels(), name="trading-alerts")
        if channel:
            await channel.send(content="🕒 **Hourly Point Price Overview**", file=file)

    except Exception as e:
        print(f"[Hourly graph error] {e}")

@tasks.loop(minutes=30)
async def log_item_price_history():
    await bot.wait_until_ready()

    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        return

    history_path = "data/item_price_history.json"
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = {}

    item_ids = {
        "xanax": "258",
        "erotic dvds": "264",
        "feathery hotel coupon": "269",
        "poison mistletoe": "2067"
    }

    now = int(time.time())
    one_week_ago = now - 7 * 86400

    for name, item_id in item_ids.items():
        try:
            url = f"https://api.torn.com/market/{item_id}?key={api_key}"
            response = requests.get(url)
            data = response.json()

            if "bazaar" not in data or not data["bazaar"]:
                continue

            lowest = data["bazaar"][0]
            price = int(lowest["cost"])

            if name not in history:
                history[name] = []

            history[name].append({"timestamp": now, "price": price})

            # Trim to 1 week
            history[name] = [entry for entry in history[name] if entry["timestamp"] >= one_week_ago]

        except Exception as e:
            print(f"[Error logging history for {name}] {e}")

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


@tasks.loop(hours=24)
async def daily_trim_item_history():
    await bot.wait_until_ready()
    trim_item_price_history()



@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=1344056482668478557)
        bot.tree.add_command(warpredict, guild=guild)
        bot.tree.add_command(autopredict, guild=guild)
        bot.tree.add_command(check_gear_perk, guild=guild)
        bot.tree.add_command(list_gear_perks, guild=guild)
        bot.tree.add_command(check_job_perk, guild=guild)
        bot.tree.add_command(list_job_perks, guild=guild)
        bot.tree.add_command(list_jobs, guild=guild)
        bot.tree.add_command(set_points_buy, guild=guild)
        bot.tree.add_command(set_points_sell, guild=guild)
        bot.tree.add_command(check_points_price, guild=guild)
        bot.tree.add_command(check_item_price, guild=guild)
        bot.tree.add_command(set_item_buy_price, guild=guild)
        bot.tree.add_command(set_item_sell_price, guild=guild)
        bot.tree.add_command(item_price_graph, guild=guild)

        synced = await bot.tree.sync(guild=guild)
        print(f"🔁 Force-synced {len(synced)} commands to guild {guild.id}")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
    
    check_point_market.start()
    post_hourly_point_graph.start()
    daily_trim_item_history.start()
    check_item_prices.start()
    log_item_price_history.start()



    print(f"✅ Bot is ready. Logged in as {bot.user}")

bot.run(os.getenv("BOT_TOKEN"))
