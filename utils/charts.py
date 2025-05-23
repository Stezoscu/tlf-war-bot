import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
from discord.ext import tasks
import discord

from constants import ITEM_HISTORY_FILE, POINT_HISTORY_FILE, TRACKED_ITEMS

@bot.tree.command(name="item_price_graph", description="Show a price trend graph for a tracked item over the last week")
@app_commands.describe(item="Tracked item name (e.g., Xanax, Erotic DVDs)")
async def item_price_graph(interaction: discord.Interaction, item: str):
    await interaction.response.defer()

    normalised = normalise_item_name(item)
    if not normalised or normalised not in TRACKED_ITEMS.values():
        supported = ", ".join(TRACKED_ITEMS.keys())
        await interaction.followup.send(f"❌ Unsupported item. Try: {supported}")
        return

    try:
        with open(ITEM_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        await interaction.followup.send("❌ No price history data found.")
        return

    if normalised not in history or not history[normalised]:
        pretty_name = next((k for k, v in TRACKED_ITEMS.items() if v == normalised), item.title())
        await interaction.followup.send(f"❌ No data found for **{pretty_name}**.")
        return

    entries = history[normalised]
    times = [datetime.utcfromtimestamp(e["timestamp"]).strftime("%d %b %H:%M") for e in entries]
    prices = [e["price"] for e in entries]

    fig, ax = plt.subplots()
    ax.plot(times, prices, marker="o", linestyle="-", label=pretty_name)
    ax.set_title(f"{pretty_name} Price Trend (Last 7 Days)")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Price (T$)")
    plt.xticks(rotation=45)
    ax.grid(True)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    file = discord.File(buf, filename="item_trend.png")
    plt.close()

    await interaction.followup.send(file=file)

@tasks.loop(hours=12)
async def post_hourly_point_graph():
    await bot.wait_until_ready()

    try:
        with open(POINT_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)

        if len(history) < 2:
            return  # Not enough data

        times = [datetime.utcfromtimestamp(e["timestamp"]).strftime("%H:%M") for e in history]
        prices = [e["price"] for e in history]

        fig, ax = plt.subplots()
        ax.plot(times, prices, label="Point Price")
        ax.set_title("Point Price - Last 24 Hours")
        ax.set_xlabel("Time (UTC)")
        ax.set_ylabel("Price (T$)")
        ax.grid(True)
        plt.xticks(rotation=45)

        buf = BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        buf.seek(0)
        file = discord.File(buf, filename="points_graph.png")
        plt.close()

        channel = discord.utils.get(bot.get_all_channels(), name="trading-alerts")
        if channel:
            await channel.send(content="🕒 **Hourly Point Price Overview**", file=file)

    except Exception as e:
        print(f"[Hourly graph error] {e}")