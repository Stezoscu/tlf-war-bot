
import discord
import os
import requests
from discord import app_commands, Interaction, File
from utils.items import fetch_item_market_price, normalise_item_name
from utils.charts import generate_item_price_graph
from utils.history import load_item_price_history
from utils.tracked_items import (
    add_tracked_item,
    remove_tracked_item,
    load_combined_items_data,
    update_item_threshold
)
from typing import Optional
import matplotlib.pyplot as plt
from io import BytesIO

@app_commands.command(name="set_item_threshold", description="Set buy and/or sell thresholds for a tracked item")
@app_commands.describe(
    item="Tracked item name (e.g., Xanax)",
    buy="Optional buy threshold price (T$)",
    sell="Optional sell threshold price (T$)"
)
async def set_item_threshold(interaction: discord.Interaction, item: str, buy: Optional[int] = None, sell: Optional[int] = None):
    try:
        if buy is None and sell is None:
            await interaction.response.send_message("⚠️ Please provide at least one of 'buy' or 'sell' thresholds.", ephemeral=True)
            return

        data = load_combined_items_data()
        normalised = normalise_item_name(item)

        if normalised not in data:
            supported = ", ".join(data.keys())
            await interaction.response.send_message(f"❌ Unsupported item. Try: {supported}", ephemeral=True)
            return

        update_item_threshold(item, buy=buy, sell=sell)

        parts = []
        if buy is not None:
            parts.append(f"Buy ≤ {buy:,} T$")
        if sell is not None:
            parts.append(f"Sell ≥ {sell:,} T$")

        await interaction.response.send_message(
            f"✅ Thresholds updated for **{item.title()}**: {' | '.join(parts)}",
            ephemeral=True
        )

    except Exception as e:
        print(f"❌ Error in set_item_threshold: {e}")
        await interaction.response.send_message("❌ An error occurred while setting the thresholds.", ephemeral=True)

@app_commands.command(name="check_item_price", description="Check current lowest item market price")
@app_commands.describe(item="Tracked item name (e.g., Xanax)")
async def check_item_price(interaction: Interaction, item: str):
    data = load_combined_items_data()
    normalised = normalise_item_name(item)

    if normalised not in data:
        supported = ", ".join(data.keys())
        await interaction.response.send_message(f"❌ Unsupported item. Try: {supported}", ephemeral=True)
        return

    item_id = data[normalised]["item_id"]
    price, quantity = fetch_item_market_price(item_id)

    if price is None:
        await interaction.response.send_message(f"⚠️ No listings for **{item.title()}**", ephemeral=True)
        return

    await interaction.response.send_message(
        f"📦 **{item.title()}** lowest market price: **{price:n}** T$ for {quantity} units"
    )

@app_commands.command(name="item_price_graph", description="Show a price trend graph for a tracked item over the last week")
@app_commands.describe(item="Name of the item to graph (e.g., Xanax)")
async def item_price_graph(interaction: Interaction, item: str):
    try:
        print(f"📈 Received /item_price_graph for item: {item}")
        tracked_items = load_combined_items_data()
        history_data = load_item_price_history()

        normalised = normalise_item_name(item)
        if normalised not in tracked_items:
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

@app_commands.command(name="add_tracked_item", description="Add a new item to track, with optional buy/sell thresholds")
@app_commands.describe(
    name="Item name (e.g., Xanax)",
    item_id="Torn Item ID (e.g., 206)",
    buy_price="Optional: Buy threshold price",
    sell_price="Optional: Sell threshold price"
)
async def add_tracked_item_command(interaction: discord.Interaction, name: str, item_id: str, buy_price: int = None, sell_price: int = None):
    try:
        success = add_tracked_item(name, item_id)

        if not success:
            await interaction.response.send_message(f"⚠️ **{name}** is already tracked.", ephemeral=True)
            return

        normalised = normalise_item_name(name)
        update_item_threshold(name, buy=buy_price, sell=sell_price)

        messages = [f"✅ **{name}** added to tracked items (ID: {item_id})."]
        if buy_price is not None:
            messages.append(f"➡️ Buy threshold set: ≤ {buy_price:,} T$")
        if sell_price is not None:
            messages.append(f"➡️ Sell threshold set: ≥ {sell_price:,} T$")

        await interaction.response.send_message("".join(messages), ephemeral=True)

    except Exception as e:
        print(f"❌ Error in add_tracked_item_command: {e}")
        await interaction.response.send_message("❌ An error occurred while adding the item.", ephemeral=True)

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
        tracked = load_combined_items_data()
        if not tracked:
            await interaction.response.send_message("ℹ️ No items are currently being tracked.", ephemeral=True)
            return

        response = "**📦 Currently Tracked Items:**"
        for name, data in tracked.items():
            item_id = data["item_id"]
            response += f"- **{name.title()}** (ID: `{item_id}`)"

        if len(response) > 2000:
            chunks = [response[i:i+1990] for i in range(0, len(response), 1990)]
            for chunk in chunks:
                await interaction.followup.send(chunk, ephemeral=True)
        else:
            await interaction.response.send_message(response, ephemeral=True)

    except Exception as e:
        print(f"❌ Error in list_tracked_items: {e}")
        await interaction.response.send_message("❌ Failed to list tracked items.", ephemeral=True)
