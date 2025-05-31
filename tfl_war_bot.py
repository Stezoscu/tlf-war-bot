import os
import discord
from discord.ext import commands
from constants import GUILD_ID, ITEM_THRESHOLD_FILE

# Import all slash commands
from commands.warpredict import warpredict, autopredict
from commands.perks import check_gear_perk, list_gear_perks, check_job_perk, list_jobs, list_job_perks
from commands.points import set_points_buy, set_points_sell, check_points_price
from commands.items import check_item_price, item_price_graph, add_tracked_item_command, remove_tracked_item_command, list_tracked_items_command, set_item_threshold
from commands.bank import deposit, withdraw, check_statement, loan_summary, bank_adjust
from commands.trains_tracker import set_trains_data_command, view_trains_data, add_received_trains
from commands.trains_auto_checker import start_train_log_checker
from commands.happy_insurance import view_insurance_timestamp, view_active_insurance, view_insurance_log
# Import tracked item commands

# Import utility functions and background tasks
from utils.thresholds import post_threshold_summary
from utils.charts import post_hourly_point_graph
from utils.tracked_items import initialise_combined_tracked_file
from utils.bank import initialise_bank_file
from utils.trains_tracker import initialise_train_file
from utils.happy_insurance import initialise_happy_insurance_file, _initialise_log_file
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
        bot.tree.add_command(set_item_threshold, guild=guild)
        bot.tree.add_command(check_item_price, guild=guild)
        bot.tree.add_command(item_price_graph, guild=guild)
        bot.tree.add_command(add_tracked_item_command, guild=guild)
        bot.tree.add_command(remove_tracked_item_command, guild=guild)
        bot.tree.add_command(list_tracked_items_command, guild=guild)
        bot.tree.add_command(deposit, guild=guild)
        bot.tree.add_command(withdraw, guild=guild)
        bot.tree.add_command(check_statement, guild=guild)
        bot.tree.add_command(loan_summary, guild=guild)
        bot.tree.add_command(bank_adjust, guild=guild)
        bot.tree.add_command(set_trains_data_command, guild=guild)  
        bot.tree.add_command(view_trains_data, guild=guild)
        bot.tree.add_command(add_received_trains,guild=guild)
        bot.tree.add_command(view_insurance_timestamp, guild=guild)  
        bot.tree.add_command(view_active_insurance, guild=guild)
        bot.tree.add_command(view_insurance_log, guild=guild)
        


        synced = await bot.tree.sync(guild=guild)
        print(f"🔁 Synced {len(synced)} commands to guild {guild.id}")

        # Perform startup tasks
        
        initialise_combined_tracked_file()
        initialise_bank_file()
        start_train_log_checker()
        initialise_happy_insurance_file()
        _initialise_log_file()
        await post_threshold_summary(bot)
        await post_hourly_point_graph(bot)
        

        # Start background loops
        start_loops(bot)
        start_train_log_checker(bot)


        print(f"✅ Bot is ready. Logged in as {bot.user}")
    except Exception as e:
        print(f"❌ Error during bot startup: {e}")


bot.run(os.getenv("BOT_TOKEN"))
