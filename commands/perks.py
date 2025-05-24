# commands/perks.py

import discord
from discord import app_commands


from utils.perks import GEAR_PERKS, JOB_PERKS

@app_commands.command(name="check_gear_perk", description="Get the perk for a specific gear item.")
@app_commands.describe(gear_name="The name of the gear item")
async def check_gear_perk(interaction: discord.Interaction, gear_name: str):
    perk_info = GEAR_PERKS.get(gear_name) or GEAR_PERKS.get(gear_name.lower())
    if perk_info:
        await interaction.response.send_message(f"**{gear_name}** perk: {perk_info}")
    else:
        await interaction.response.send_message(f"⚠️ No perk information found for **{gear_name}**.")

@app_commands.command(name="list_gear_perks", description="List all gear items and their perks.")
async def list_gear_perks(interaction: discord.Interaction):
    message = "**Gear Perks:**\n"
    for gear, perk in GEAR_PERKS.items():
        message += f"- **{gear}**: {perk}\n"
    await interaction.response.send_message(message)

@app_commands.command(name="check_job_perk", description="Show the perk(s) provided by a specific job.")
@app_commands.describe(job_name="The name of the job")
async def check_job_perk(interaction: discord.Interaction, job_name: str):
    perk_info = JOB_PERKS.get(job_name) or JOB_PERKS.get(job_name.lower())
    if perk_info:
        await interaction.response.send_message(f"**{job_name}** perk: {perk_info}")
    else:
        await interaction.response.send_message(f"⚠️ No perk information found for job **{job_name}**.")

@app_commands.command(name="list_jobs", description="List all available jobs.")
async def list_jobs(interaction: discord.Interaction):
    job_names = JOB_PERKS.keys()
    await interaction.response.send_message("**Available Jobs:** " + ", ".join(job_names))

@app_commands.command(name="list_job_perks", description="List all jobs with their respective perks.")
async def list_job_perks(interaction: discord.Interaction):
    message = "**Job Perks:**\n"
    for job, perk in JOB_PERKS.items():
        message += f"- **{job}**: {perk}\n"
    await interaction.response.send_message(message)
