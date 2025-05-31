# commands/trains_auto_checker.py

from discord.ext import tasks
from utils.trains_tracker import update_received_trains_from_logs

def start_train_log_checker():
    @tasks.loop(minutes=5)
    async def check_logs_for_trains():
        print("🔄 Checking for new train logs...")
        update_received_trains_from_logs()

    check_logs_for_trains.start()
