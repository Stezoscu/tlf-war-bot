import discord
from discord import app_commands
from discord.ext import commands
from utils.trains_tracker import set_train_data, get_train_data, update_trains_received

YOUR_DISCORD_USER_ID = 521438347705450507  # Replace with your actual ID

@app_commands.command(name="set_trains_data", description="Set train tracker data (bought, received, cost).")
@app_commands.describe(
    trains_bought="Number of trains bought",
    trains_received="Number of trains received",
    cost_per_train="Cost per train"
)
async def set_trains_data_command(
    interaction: discord.Interaction,
    trains_bought: int = None,
    trains_received: int = None,
    cost_per_train: int = None
):
    if interaction.user.id != YOUR_DISCORD_USER_ID:
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    set_train_data(trains_bought, trains_received, cost_per_train)
    await interaction.response.send_message("✅ Train tracker data updated!", ephemeral=True)

@app_commands.command(name="view_trains_data", description="View the current train tracker data.")
async def view_trains_data(interaction: discord.Interaction):
    data = get_train_data()
    msg = (
        f"📊 **Train Tracker Data**\n"
        f"Bought: {data['trains_bought']:n}\n"
        f"Received: {data['trains_received']:n}\n"
        f"Cost per Train: ${data['cost_per_train']:n}"
    )
    await interaction.response.send_message(msg, ephemeral=True)

@app_commands.command(name="add_received_trains", description="Add to the count of received company trains.")
@app_commands.describe(count="Number of new trains received to add.")
async def add_received_trains(interaction: discord.Interaction, count: int):
    if interaction.user.id != YOUR_DISCORD_USER_ID:
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    if count <= 0:
        await interaction.response.send_message("❌ Count must be positive.", ephemeral=True)
        return

    update_trains_received(count)
    data = get_train_data()
    await interaction.response.send_message(
        f"✅ Added {count:n} to received trains.\nTotal received now: {data['trains_received']:n}", ephemeral=True
    )
