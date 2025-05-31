from discord.ext import tasks
from utils.trains_tracker import update_received_trains_from_logs
from utils.happy_insurance import (
    check_xanax_insurance, load_last_timestamp, save_last_timestamp,
    save_insurance_logs, post_insurance_to_channel
)

def start_train_log_checker(bot):
    @tasks.loop(minutes=5)
    async def check_logs():
        print("🔄 Checking for new train logs...")
        update_received_trains_from_logs()

        print("🔄 Checking for new happy insurance logs...")
        last_ts = load_last_timestamp()
        new_payments = check_xanax_insurance(last_ts)

        if new_payments:
            latest_ts = max(p["timestamp"] for p in new_payments)
            save_last_timestamp(latest_ts)
            save_insurance_logs(new_payments)

            for payment in new_payments:
                await post_insurance_to_channel(bot, payment)
        else:
            print("ℹ️ No new happy insurance payments.")

    check_logs.start()