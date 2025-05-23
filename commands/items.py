# commands/items.py
import discord
from utils import thresholds
from utils.predictor import prices  # Utility modules for threshold storage and price data

async def set_item_buy_price(interaction: discord.Interaction, item: str, price: int):
    """Set the buy price threshold for a given item."""
    thresholds.set_item_buy_threshold(item, price)
    await interaction.response.send_message(f"Buy threshold for **{item}** set to ${price:,}.")

async def set_item_sell_price(interaction: discord.Interaction, item: str, price: int):
    """Set the sell price threshold for a given item."""
    thresholds.set_item_sell_threshold(item, price)
    await interaction.response.send_message(f"Sell threshold for **{item}** set to ${price:,}.")

async def check_item_price(interaction: discord.Interaction, item: str):
    """Check the current market price of a given item."""
    current_price = prices.get_item_price(item)
    await interaction.response.send_message(f"Current price of **{item}** is ${current_price:,} each.")

async def item_price_graph(interaction: discord.Interaction, item: str):
    """Display a price history graph for the specified item."""
    graph_url = prices.generate_price_graph(item)  # Assume this returns a URL or file for the graph
    await interaction.response.send_message(f"Price history for **{item}**: {graph_url}")
