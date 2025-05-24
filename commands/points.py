# commands/points.py

import discord
from discord import app_commands


from utils import thresholds
from utils import charts as prices

@app_commands.command(name="set_points_buy", description="Set the buy price threshold for points.")
@app_commands.describe(threshold="The price (T$) at or below which you want to buy points")
async def set_points_buy(interaction: discord.Interaction, threshold: int):
    thresholds.set_points_buy_threshold(threshold)
    await interaction.response.send_message(f"Points buy threshold set to ${threshold:,} per point.")

@app_commands.command(name="set_points_sell", description="Set the sell price threshold for points.")
@app_commands.describe(threshold="The price (T$) at or above which you want to sell points")
async def set_points_sell(interaction: discord.Interaction, threshold: int):
    thresholds.set_points_sell_threshold(threshold)
    await interaction.response.send_message(f"Points sell threshold set to ${threshold:,} per point.")

@app_commands.command(name="check_points_price", description="Check the current market price of points.")
async def check_points_price(interaction: discord.Interaction):
    current_price = prices.get_points_price()
    await interaction.response.send_message(f"Current points market price is ${current_price:,} per point.")
