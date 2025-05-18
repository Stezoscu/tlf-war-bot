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

# Load gear perks from JSON
with open("data/gear_perks.json", "r", encoding="utf-8") as f:
    gear_perks = json.load(f)
    

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
        "current_hour": current_hour,
        "your_score": your_score,
        "current_lead": current_lead,
        "starting_goal": starting_goal
    }

# ---- Slash Commands ----

@bot.tree.command(name="warpredict", description="Manually predict Torn war end.")
@app_commands.describe(
    current_hour="How many hours has the war been running?",
    current_lead="Your current lead (your score - enemy score)",
    your_score="Your faction's score",
    starting_goal="Starting lead target (e.g., 3000)"
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

# ---- Sync and run ----

@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=1344056482668478557)  # your server ID
        synced = await bot.tree.sync(guild=guild)
        print(f"🔁 Synced {len(synced)} commands to guild.")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
    print(f"✅ Bot is ready. Logged in as {bot.user}")

bot.run(os.getenv("BOT_TOKEN"))
