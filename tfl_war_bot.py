import discord
from discord import app_commands
from discord.ext import commands
import numpy as np
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- War prediction logic ---
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

# --- Slash command registration ---
@bot.tree.command(name="warpredict", description="Predict when your Torn war will end.")
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
        f"📅 War ends at **hour {result['war_end_hour']}** (in {result['hours_remaining']}h)\n"
        f"🏁 Final Scores:\n"
        f" - You: **{result['your_final_score']}**\n"
        f" - Opponent: **{result['opponent_final_score']}**\n"
        f"📊 Final Lead: **{result['final_lead']}**"
    )

# --- Sync commands when the bot is ready ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot is ready. Logged in as {bot.user}.")

# --- Start the bot ---
bot.run(os.getenv("BOT_TOKEN"))