import os
import time
import requests
import numpy as np
import discord
from discord import app_commands
from discord.ext import commands

# --- Setup bot ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Prediction logic ---
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

# --- Manual prediction command ---
@bot.tree.command(name="warpredict", description="Predict Torn war outcome from manual inputs")
@app_commands.describe(
    current_hour="How many hours the war has been running",
    current_lead="Current lead (your score - enemy score)",
    your_score="Your faction's score",
    starting_goal="Starting score goal (target)"
)
async def warpredict(interaction: discord.Interaction, current_hour: float, current_lead: int, your_score: int, starting_goal: int):
    result = predict_war_end(current_hour, current_lead, your_score, starting_goal)
    await interaction.response.send_message(
        f"🧠 **TLF Torn War Predictor**\n"
        f"📅 War ends at hour **{result['war_end_hour']}** (in {result['hours_remaining']}h)\n"
        f"🏁 Final Scores:\n"
        f" - You: **{result['your_final_score']}**\n"
        f" - Opponent: **{result['opponent_final_score']}**\n"
        f"📊 Final Lead: **{result['final_lead']}**"
    )

# --- Torn API v2 Auto Prediction ---
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
        "current_hour": current_hour,
        "your_score": your_score,
        "current_lead": current_lead,
        "starting_goal": starting_goal
    }

@bot.tree.command(name="autopredict", description="Auto predict Torn war outcome using live API data")
async def autopredict(interaction: discord.Interaction):
    try:
        data = fetch_v2_war_data()
        result = predict_war_end(
            data["current_hour"],
            data["current_lead"],
            data["your_score"],
            data["starting_goal"]
        )
        await interaction.response.send_message(
            f"📡 **Auto Prediction Based on Live Torn Data**\n"
            f"🕓 War Duration: **{data['current_hour']} hours**\n"
            f"📊 Current Score: **{data['your_score']}** | Lead: **{data['current_lead']}**\n"
            f"🎯 Target: **{data['starting_goal']}**\n"
            f"📅 Predicted End: **hour {result['war_end_hour']}** (in {result['hours_remaining']}h)\n"
            f"🏁 Final Score Estimate:\n"
            f" - You: **{result['your_final_score']}**\n"
            f" - Opponent: **{result['opponent_final_score']}**"
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}")

# --- On Ready (sync commands) ---
@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=1344056482668478557)  # Replace with your real server ID
        synced = await bot.tree.sync(guild=guild)
        print(f"🔁 Synced {len(synced)} commands to guild.")
    except Exception as e:
        print(f"❌ Error syncing guild commands: {e}")

    try:
        synced_global = await bot.tree.sync()
        print(f"🌍 Synced {len(synced_global)} global commands.")
    except Exception as e:
        print(f"❌ Error syncing global commands: {e}")

    print(f"✅ Bot is ready. Logged in as {bot.user}.")

# --- Run bot ---
bot.run(os.getenv("BOT_TOKEN"))