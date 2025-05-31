import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from utils.happy_insurance import load_last_timestamp
from utils.happy_insurance import get_active_insurance_logs
from utils.happy_insurance import get_recent_insurance_logs

@app_commands.command(name="view_insurance_timestamp", description="View last checked insurance payment timestamp.")
async def view_insurance_timestamp(interaction: discord.Interaction):
    last_ts = load_last_timestamp()
    await interaction.response.send_message(f"🗓️ Last checked insurance log timestamp: {last_ts}", ephemeral=True)

@app_commands.command(name="view_active_insurance", description="View active happy insurance cover.")
async def view_active_insurance(interaction: discord.Interaction):
    active = get_active_insurance_logs()
    if not active:
        await interaction.response.send_message("ℹ️ No active happy insurance covers.", ephemeral=True)
        return

    msg = "**🛡️ Active Happy Insurance Covers:**\n"
    for log in active:
        dt = datetime.fromtimestamp(log["timestamp"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        end_dt = datetime.fromisoformat(log["coverage_end"]).strftime("%Y-%m-%d %H:%M:%S UTC")
        msg += f"👤 {log['sender_id']} | 🕒 {dt} - {end_dt} | 📝 {log['message'] or '(no message)'}\n"

    await interaction.response.send_message(msg, ephemeral=True)

@app_commands.command(name="view_insurance_log", description="View insurance payments from the last 24 hours.")
@app_commands.describe(hours="Number of hours to look back, default 24.")
async def view_insurance_log(interaction: discord.Interaction, hours: int = 24):
    recent = get_recent_insurance_logs(hours=hours)
    if not recent:
        await interaction.response.send_message("ℹ️ No insurance payments in that time frame.", ephemeral=True)
        return

    msg = f"**🗓️ Insurance payments in the last {hours} hour(s):**\n"
    for log in recent:
        dt = datetime.fromtimestamp(log["timestamp"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        end_dt = datetime.fromisoformat(log["coverage_end"]).strftime("%Y-%m-%d %H:%M:%S UTC")
        msg += f"👤 {log['sender_id']} | 🕒 {dt} - {end_dt} | 📝 {log['message'] or '(no message)'}\n"

    await interaction.response.send_message(msg, ephemeral=True)