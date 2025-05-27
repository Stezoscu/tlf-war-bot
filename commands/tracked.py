import discord
from discord import app_commands
from utils.tracked_items import (
    load_tracked_items,
    add_tracked_item,
    remove_tracked_item
)

@app_commands.command(name="list_tracked_items", description="List all currently tracked items and their IDs")
async def list_tracked_items(interaction: discord.Interaction):
    items = load_tracked_items()
    if not items:
        await interaction.response.send_message("📦 No items are currently being tracked.")
        return
    message = "**📋 Tracked Items:**\n"
    for name, item_id in items.items():
        message += f"- {name} (ID: {item_id})\n"
    await interaction.response.send_message(message)

@app_commands.command(name="add_tracked_item", description="Add a new item to the tracked list")
@app_commands.describe(name="Item name", item_id="Item ID from Torn")
async def add_item(interaction: discord.Interaction, name: str, item_id: int):
    success, msg = add_tracked_item(name, item_id)
    await interaction.response.send_message(msg)

@app_commands.command(name="remove_tracked_item", description="Remove an item from the tracked list")
@app_commands.describe(name="Item name to remove")
async def remove_item(interaction: discord.Interaction, name: str):
    success, msg = remove_tracked_item(name)
    await interaction.response.send_message(msg)
