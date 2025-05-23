# commands/points.py
import discord
from utils import thresholds
from utils import prices
  # Import utility modules for thresholds and price checks

async def set_points_buy(interaction: discord.Interaction, threshold: int):
    """Set the buy price threshold for points."""
    # Update the threshold using a utility function and respond to the user
    thresholds.set_points_buy_threshold(threshold)
    await interaction.response.send_message(f"Points buy threshold set to ${threshold:,} per point.")

async def set_points_sell(interaction: discord.Interaction, threshold: int):
    """Set the sell price threshold for points."""
    thresholds.set_points_sell_threshold(threshold)
    await interaction.response.send_message(f"Points sell threshold set to ${threshold:,} per point.")

async def check_points_price(interaction: discord.Interaction):
    """Check the current market price of points."""
    current_price = prices.get_points_price()  # Retrieve current points price from utils
    await interaction.response.send_message(f"Current points market price is ${current_price:,} per point.")
