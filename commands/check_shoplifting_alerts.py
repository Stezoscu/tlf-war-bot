import discord
from discord import app_commands
import json
import os

ALERT_FILE_PATH = "/mnt/data/shoplifting_last_alerted.json"

@app_commands.command(name="check_shoplifting_alerts", description="See which shops have already been alerted.")
async def check_shoplifting_alerts(interaction: discord.Interaction):
    if not os.path.exists(ALERT_FILE_PATH):
        await interaction.response.send_message("⚠️ No alert file found.", ephemeral=True)
        return

    try:
        with open(ALERT_FILE_PATH, "r") as f:
            alerted = json.load(f)
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Failed to load alert file: {e}", ephemeral=True)
        return

    if not alerted:
        await interaction.response.send_message("✅ No shops are currently flagged as alerted.", ephemeral=True)
    else:
        msg = "🛑 Currently alerted shops:\n" + "\n".join(f"- {shop.replace('_', ' ').title()}" for shop in alerted)
        await interaction.response.send_message(msg, ephemeral=True)
