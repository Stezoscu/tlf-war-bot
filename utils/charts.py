import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
from discord.ext import tasks
import discord
import requests

from constants import ITEM_HISTORY_FILE, POINT_HISTORY_FILE
from utils.history import load_item_price_history
from utils.normalise import normalise_item_name
from utils.tracked_items import load_combined_items_data


async def generate_item_price_graph(interaction: discord.Interaction, item: str):
    await interaction.response.defer()

    combined_items = load_combined_items_data()
    history_data = load_item_price_history()

    normalised = normalise_item_name(item)
    if not normalised or normalised not in combined_items:
        supported = ", ".join(name.title() for name in combined_items.keys())
        await interaction.followup.send(f"❌ Unsupported item. Try one of: {supported}")
        return

    price_history = history_data.get(normalised, [])
    pretty_name = item.title()

    if not price_history:
        await interaction.followup.send(f"❌ No data found for **{pretty_name}**.")
        return

    times = [datetime.utcfromtimestamp(entry["timestamp"]).strftime("%d %b %H:%M") for entry in price_history]
    prices = [entry["price"] for entry in price_history]

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
async def post_hourly_point_graph(bot):
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


def get_points_price():
    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        raise ValueError("Missing TORN_API_KEY")

    url = f"https://api.torn.com/market/?selections=pointsmarket&key={api_key}"
    response = requests.get(url)
    data = response.json()

    if "pointsmarket" not in data or not data["pointsmarket"]:
        raise ValueError("No pointsmarket data found")

    lowest_offer = min(data["pointsmarket"].values(), key=lambda x: x["cost"])
    return lowest_offer["cost"]
