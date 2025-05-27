import discord
import os
import requests
from discord import app_commands
from discord import Interaction
from constants import TRACKED_ITEMS, ITEM_IDS
from utils.thresholds import set_item_buy_threshold, set_item_sell_threshold
from utils.items import fetch_item_market_price
from utils.items import normalise_item_name
from utils.charts import generate_item_price_graph
from utils.tracked_items import load_tracked_items

# 📌 Slash command: /set_item_buy_price
@app_commands.command(name="set_item_buy_price", description="Set buy threshold for an item")
@app_commands.describe(item="Tracked item name (e.g., Xanax)", price="Buy threshold price")
async def set_item_buy_price(interaction: discord.Interaction, item: str, price: int):
    normalised = normalise_item_name(item)
    if not normalised or normalised not in TRACKED_ITEMS.values():
        supported = ", ".join(TRACKED_ITEMS.keys())
        await interaction.response.send_message(f"❌ Unsupported item. Try: {supported}", ephemeral=True)
        return

    set_item_buy_threshold(normalised, price)
    await interaction.response.send_message(f"✅ Buy threshold set for **{item.title()}**: ≤ {price:,} T$", ephemeral=True)

# 📌 Slash command: /set_item_sell_price
@app_commands.command(name="set_item_sell_price", description="Set sell threshold for an item")
@app_commands.describe(item="Tracked item name (e.g., Xanax)", price="Sell threshold price")
async def set_item_sell_price(interaction: discord.Interaction, item: str, price: int):
    normalised = normalise_item_name(item)
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
@app_commands.describe(item="Tracked item name (e.g., Xanax)")
async def item_price_graph(interaction: discord.Interaction, item: str):
    normalised = normalise_item_name(item)
    if not normalised or normalised not in TRACKED_ITEMS.values():
        supported = ", ".join(TRACKED_ITEMS.keys())
        await interaction.response.send_message(f"❌ Unsupported item. Try: {supported}")
        return

    graph_bytes = generate_item_price_graph(normalised)

    if not graph_bytes:
        await interaction.response.send_message(f"❌ No price history available for **{item.title()}**.")
        return

    file = discord.File(graph_bytes, filename=f"{normalised}_trend.png")
    await interaction.response.send_message(
        content=f"📈 Price trend for **{item.title()}** over the last 7 days:",
        file=file
    )
