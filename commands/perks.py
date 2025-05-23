# commands/perks.py
import discord
from constants import GEAR_PERKS, JOB_PERKS  # Assume constants defines dicts for gear and job perks

async def check_gear_perk(interaction: discord.Interaction, gear_name: str):
    """Get details about the perk/bonus of a specific gear item."""
    perk_info = GEAR_PERKS.get(gear_name) or GEAR_PERKS.get(gear_name.lower())
    if perk_info:
        await interaction.response.send_message(f"**{gear_name}** perk: {perk_info}")
    else:
        await interaction.response.send_message(f"⚠️ No perk information found for **{gear_name}**.")

async def list_gear_perks(interaction: discord.Interaction):
    """List all gear items and their perks."""
    message = "**Gear Perks:**\n"
    for gear, perk in GEAR_PERKS.items():
        message += f"- **{gear}**: {perk}\n"
    await interaction.response.send_message(message)

async def check_job_perk(interaction: discord.Interaction, job_name: str):
    """Show the perk(s) provided by a specific job."""
    perk_info = JOB_PERKS.get(job_name) or JOB_PERKS.get(job_name.lower())
    if perk_info:
        await interaction.response.send_message(f"**{job_name}** perk: {perk_info}")
    else:
        await interaction.response.send_message(f"⚠️ No perk information found for job **{job_name}**.")

async def list_jobs(interaction: discord.Interaction):
    """List all available jobs."""
    job_names = JOB_PERKS.keys()
    await interaction.response.send_message("**Available Jobs:** " + ", ".join(job_names))

async def list_job_perks(interaction: discord.Interaction):
    """List all jobs with their respective perks."""
    message = "**Job Perks:**\n"
    for job, perk in JOB_PERKS.items():
        message += f"- **{job}**: {perk}\n"
    await interaction.response.send_message(message)
