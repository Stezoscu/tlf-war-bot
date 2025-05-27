import discord
import os
import requests
from discord import app_commands
from discord import Interaction
from discord import File
from utils.thresholds import set_item_buy_threshold, set_item_sell_threshold
from utils.items import fetch_item_market_price
from utils.items import normalise_item_name
from utils.charts import generate_item_price_graph
from utils.tracked_items import load_tracked_items
import matplotlib.pyplot as plt
from io import BytesIO
from utils.history import load_item_price_history
from utils.tracked_items import add_tracked_item, remove_tracked_item, load_tracked_items

# 📌 Slash command: /set_item_buy_price
@app_commands.command(name="set_item_buy_price", description="Set buy threshold for an item")
@app_commands.describe(item="Tracked item name (e.g., Xanax)", price="Buy threshold price")
async def set_item_buy_price(interaction: discord.Interaction, item: str, price: int):
    normalised = normalise_item_name(item)
    tracked_items = load_tracked_items()
    if not normalised or normalised not in tracked_items.values():
        supported = ", ".join(tracked_items.keys())
        await interaction.response.send_message(f"❌ Unsupported item. Try: {supported}", ephemeral=True)
        return

    set_item_buy_threshold(normalised, price)
    await interaction.response.send_message(f"✅ Buy threshold set for **{item.title()}**: ≤ {price:,} T$", ephemeral=True)

# 📌 Slash command: /set_item_sell_price
@app_commands.command(name="set_item_sell_price", description="Set sell threshold for an item")
@app_commands.describe(item="Tracked item name (e.g., Xanax)", price="Sell threshold price")
async def set_item_sell_price(interaction: discord.Interaction, item: str, price: int):
    normalised = normalise_item_name(item)
    TRACKED_ITEMS = tracked_items = load_tracked_items()
    if not normalised or normalised not in TRACKED_ITEMS.values():
        supported = ", ".join(TRACKED_ITEMS.keys())
        await interaction.response.send_message(f"❌ Unsupported item. Try: {supported}", ephemeral=True)
        return

    set_item_sell_threshold(normalised, price)
    await interaction.response.send_message(f"✅ Sell threshold set for **{item.title()}**: ≥ {price:,} T$", ephemeral=True)

# 📌 Slash command: /check_item_price
@app_commands.command(name="check_item_price", description="Check the current lowest item market price of a tracked item")
@app_commands.describe(item="Name of the item (e.g., Xanax)")
async def check_item_price(interaction: Interaction, item: str):
    try:
        print(f"🔍 Received /check_item_price for item: {item}")

        # Load tracked items from JSON
        tracked_items = load_tracked_items()

        # Normalise input
        normalised = normalise_item_name(item)

        # Find match ignoring case
        match = next(
            ((pretty_name, item_id) for pretty_name, item_id in tracked_items.items()
             if pretty_name.lower() == normalised),
            None
        )

        if not match:
            supported = ", ".join(tracked_items.keys())
            await interaction.response.send_message(f"❌ Unsupported item. Try: {supported}", ephemeral=True)
            return

        pretty_name, item_id = match
        price, quantity = fetch_item_market_price(item_id)

        if price is None:
            await interaction.response.send_message(
                f"⚠️ No item market listings found for **{pretty_name}**.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"📦 **{pretty_name}** lowest item market price: **{price:n}** T$ for {quantity} units"
        )

    except Exception as e:
        print(f"❌ Error fetching item price: {e}")
        await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)

    except Exception as e:
        print(f"❌ Error in check_item_price: {e}")
        await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)

# 📌 Slash command: /item_price_graph
@app_commands.command(name="item_price_graph", description="Show a price trend graph for a tracked item over the last week")
@app_commands.describe(item="Name of the item to graph (e.g., Xanax)")
async def item_price_graph(interaction: Interaction, item: str):
    try:
        print(f"📈 Received /item_price_graph for item: {item}")
        tracked_items = load_tracked_items()
        history_data = load_item_price_history()

        normalised = normalise_item_name(item)
        if normalised not in tracked_items.values():
            supported = ", ".join(tracked_items.keys())
            await interaction.response.send_message(
                f"❌ Item not tracked. Try one of: {supported}", ephemeral=True
            )
            return

        price_history = history_data.get(normalised, [])
        if not price_history:
            await interaction.response.send_message(
                f"⚠️ No price history available for **{item.title()}**", ephemeral=True
            )
            return

        timestamps = [entry["timestamp"] for entry in price_history]
        prices = [entry["price"] for entry in price_history]

        plt.figure()
        plt.plot(timestamps, prices, marker="o")
        plt.title(f"Price Trend for {item.title()}")
        plt.xlabel("Timestamp")
        plt.ylabel("Price (T$)")
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()

        file = File(fp=buf, filename="item_price_graph.png")
        await interaction.response.send_message(
            content=f"📊 Price trend for **{item.title()}** over the past week:",
            file=file
        )

    except Exception as e:
        print(f"❌ Error in /item_price_graph: {e}")
        await interaction.response.send_message("❌ An error occurred while generating the graph.", ephemeral=True)

@app_commands.command(name="add_tracked_item", description="Add a new item to the tracked item list (max 20)")
@app_commands.describe(name="Item name (e.g., Xanax)", item_id="Torn Item ID (e.g., 206)")
async def add_tracked_item_command(interaction: Interaction, name: str, item_id: str):
    try:
        current = load_tracked_items()
        if len(current) >= 20:
            await interaction.response.send_message(
                "❌ Cannot add item — max of 20 tracked items reached.", ephemeral=True
            )
            return

        success = add_tracked_item(name, item_id)
        if success:
            await interaction.response.send_message(
                f"✅ **{name.title()}** added to tracked items (ID: {item_id})", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Item **{name.title()}** already exists in the tracked list.", ephemeral=True
            )
    except Exception as e:
        print(f"❌ Error in add_tracked_item: {e}")
        await interaction.response.send_message("❌ Failed to add item.", ephemeral=True)


@app_commands.command(name="remove_tracked_item", description="Remove an item from the tracked list")
@app_commands.describe(name="Item name (e.g., Xanax)")
async def remove_tracked_item_command(interaction: Interaction, name: str):
    try:
        success = remove_tracked_item(name)
        if success:
            await interaction.response.send_message(f"✅ **{name.title()}** removed from tracked items.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Item **{name.title()}** not found in the tracked list.", ephemeral=True)
    except Exception as e:
        print(f"❌ Error in remove_tracked_item: {e}")
        await interaction.response.send_message("❌ Failed to remove item.", ephemeral=True)

@app_commands.command(name="list_tracked_items", description="List all currently tracked items and their Torn IDs")
async def list_tracked_items_command(interaction: Interaction):
    try:
        tracked = load_tracked_items()
        if not tracked:
            await interaction.response.send_message("ℹ️ No items are currently being tracked.", ephemeral=True)
            return

        response = "**📦 Currently Tracked Items:**\n"
        for name, item_id in tracked.items():
            response += f"- **{name.title()}** (ID: `{item_id}`)\n"

                # Handle Discord's 2000 character limit gracefully
        if len(response) > 2000:
            chunks = [response[i:i+1990] for i in range(0, len(response), 1990)]
            for chunk in chunks:
                await interaction.followup.send(chunk, ephemeral=True)
        else:
            await interaction.response.send_message(response, ephemeral=True)

    except Exception as e:
        print(f"❌ Error in list_tracked_items: {e}")
        await interaction.response.send_message("❌ Failed to list tracked items.", ephemeral=True)