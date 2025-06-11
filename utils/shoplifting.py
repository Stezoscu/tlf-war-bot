import aiohttp
import asyncio
from discord import TextChannel
from discord.ext import tasks
import discord
import os

TORN_API_KEY = os.getenv("TORN_API_KEY")

SHOPLIFTING_ALERT_CHANNEL = "shoplifting-alert"

async def fetch_shoplifting_data():
    url = f"https://api.torn.com/torn/?selections=shoplifting&key={TORN_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

@tasks.loop(minutes=1)
async def check_shoplifting(bot):
    data = await fetch_shoplifting_data()
    shop_data = data.get("shoplifting", {})

    for shop, security_list in shop_data.items():
        if security_list and all(s.get("disabled") for s in security_list):
            # Shop is fully vulnerable
            channel: TextChannel = discord.utils.get(bot.get_all_channels(), name=SHOPLIFTING_ALERT_CHANNEL)
            if channel:
                await channel.send(
                    f"🛒 **{shop.replace('_', ' ').title()}** is currently **unguarded and has all cameras disabled!**"
                )