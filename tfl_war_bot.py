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
from datetime import datetime
from pathlib import Path
from discord.ext import tasks
import asyncio

# Path to store thresholds
THRESHOLDS_FILE = "data/point_thresholds.json"

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

        # Check the pointsmarket structure
        if "pointsmarket" not in data:
            await interaction.response.send_message("❌ No 'pointsmarket' field found in API response.")
            return

        if not isinstance(data["pointsmarket"], list) or len(data["pointsmarket"]) == 0:
            await interaction.response.send_message("❌ No point listings currently found.")
            return

        # Attempt to extract the cheapest listing
        first_listing = data["pointsmarket"][0]
        price = first_listing.get("cost")
        quantity = first_listing.get("quantity", "N/A")

        if price is None or not isinstance(price, int):
            await interaction.response.send_message("❌ Invalid price data from API.")
            return

        await interaction.response.send_message(
            f"📈 **Current Point Price:** {price:n} T$ per point\n📦 Quantity Available: {quantity}"
        )

    except Exception as e:
        await interaction.response.send_message(f"❌ Error fetching price: {e}")

        

@tasks.loop(minutes=5)
async def check_point_market():
    await bot.wait_until_ready()

    thresholds = load_thresholds()
    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        return

    try:
        url = f"https://api.torn.com/market/?selections=pointsmarket&key={api_key}"
        response = requests.get(url)
        data = response.json()

        price = int(data["pointsmarket"][0]["cost"])

        channel = discord.utils.get(bot.get_all_channels(), name="trading_alerts")
        if channel:
            if thresholds["buy"] and price <= thresholds["buy"]:
                await channel.send(f"💰 **Points are cheap!** Current price: **{price:n}** T$ (≤ {thresholds['buy']})")
            if thresholds["sell"] and price >= thresholds["sell"]:
                await channel.send(f"🔥 **Points are expensive!** Current price: **{price:n}** T$ (≥ {thresholds['sell']})")

    except Exception as e:
        print(f"[Error checking point market] {e}")

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

        synced = await bot.tree.sync(guild=guild)
        print(f"🔁 Force-synced {len(synced)} commands to guild {guild.id}")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
    
    check_point_market.start()
    print(f"✅ Bot is ready. Logged in as {bot.user}")

bot.run(os.getenv("BOT_TOKEN"))
