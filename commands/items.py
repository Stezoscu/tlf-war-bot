import discord
from discord import app_commands
from discord import Interaction
from constants import TRACKED_ITEMS, ITEM_IDS
from utils.thresholds import set_item_buy_threshold, set_item_sell_threshold
from utils.items import fetch_item_market_price
from utils.items import normalise_item_name
from utils.charts import generate_item_price_graph

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
@app_commands.command(name="check_item_price", description="Check market price for a tracked item")
@app_commands.describe(item="The name of the item to check (e.g. Xanax)")
async def check_item_price(interaction: Interaction, item: str):
    try:
        print(f"🔍 Received /check_item_price for item: {item}")
        normalised = normalise_item_name(item)

        if not normalised or normalised not in TRACKED_ITEMS.values():
            supported = ", ".join(TRACKED_ITEMS.keys())
            await interaction.response.send_message(
                f"❌ Unsupported item. Try: {supported}", ephemeral=True
            )
            return

        price, quantity = fetch_item_market_price(normalised)
        if price is None:
            await interaction.response.send_message(
                f"⚠️ No item market listings found for **{item.title()}**.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"📦 **{item.title()}** is currently selling for **{price:,} T$** "
            f"(Quantity: {quantity})"
        )

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
