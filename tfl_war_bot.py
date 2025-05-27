import os
import discord
from discord.ext import commands
from constants import GUILD_ID, ITEM_THRESHOLD_FILE

# Import all slash commands
from commands.warpredict import warpredict, autopredict
from commands.perks import check_gear_perk, list_gear_perks, check_job_perk, list_jobs, list_job_perks
from commands.points import set_points_buy, set_points_sell, check_points_price
from commands.items import set_item_buy_price, set_item_sell_price, check_item_price, item_price_graph, add_tracked_item_command, remove_tracked_item_command, list_tracked_items_command
# Import tracked item commands

# Import utility functions and background tasks
from utils.thresholds import clean_item_thresholds, post_threshold_summary
from utils.charts import post_hourly_point_graph
from utils.check_loops import (
    start_loops,  # This will start all loops and inject bot
)


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)

        # Register all commands with the guild
        bot.tree.add_command(warpredict, guild=guild)
        bot.tree.add_command(autopredict, guild=guild)
        bot.tree.add_command(check_gear_perk, guild=guild)
        bot.tree.add_command(list_gear_perks, guild=guild)
        bot.tree.add_command(check_job_perk, guild=guild)
        bot.tree.add_command(list_jobs, guild=guild)
        bot.tree.add_command(list_job_perks, guild=guild)
        bot.tree.add_command(set_points_buy, guild=guild)
        bot.tree.add_command(set_points_sell, guild=guild)
        bot.tree.add_command(check_points_price, guild=guild)
        bot.tree.add_command(set_item_buy_price, guild=guild)
        bot.tree.add_command(set_item_sell_price, guild=guild)
        bot.tree.add_command(check_item_price, guild=guild)
        bot.tree.add_command(item_price_graph, guild=guild)
        bot.tree.add_command(add_tracked_item_command, guild=guild)
        bot.tree.add_command(remove_tracked_item_command, guild=guild)
        bot.tree.add_command(list_tracked_items_command, guild=guild)

        synced = await bot.tree.sync(guild=guild)
        print(f"🔁 Synced {len(synced)} commands to guild {guild.id}")

        # Perform startup tasks
        clean_item_thresholds()
        await post_threshold_summary(bot)
        await post_hourly_point_graph(bot)

        # Start background loops
        start_loops(bot)

        print(ITEM_THRESHOLD_FILE)

        print(f"✅ Bot is ready. Logged in as {bot.user}")
    except Exception as e:
        print(f"❌ Error during bot startup: {e}")


bot.run(os.getenv("BOT_TOKEN"))
