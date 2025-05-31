import os
import json
import requests
from datetime import datetime, timedelta, timezone
import discord

TORN_API_KEY = os.getenv("TORN_API_KEY")
TORN_LOG_URL = f"https://api.torn.com/user/?selections=log&key={TORN_API_KEY}"

HAPPY_INSURANCE_FILE = "/mnt/data/happy_insurance.json"  # last checked timestamp
HAPPY_INSURANCE_LOG_FILE = "/mnt/data/happy_insurance_log.json"  # all logs

def _initialise_log_file():
    if not os.path.exists(HAPPY_INSURANCE_LOG_FILE):
        with open(HAPPY_INSURANCE_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        print("✅ Created happy insurance log JSON file.")

def fetch_logs():
    response = requests.get(TORN_LOG_URL)
    data = response.json()
    return data.get("log", {})

def check_xanax_insurance(last_timestamp):
    logs = fetch_logs()
    new_payments = []

    for log_id, log_entry in logs.items():
        if log_entry.get("title") == "Item receive" and "data" in log_entry:
            data = log_entry["data"]
            items = data.get("items", [])
            timestamp = log_entry.get("timestamp", 0)

            if timestamp <= last_timestamp:
                continue

            for item in items:
                if item.get("id") == 206:  # Xanax
                    sender_id = data.get("sender")
                    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    coverage_end = dt + timedelta(hours=3)
                    message = data.get("message", "")

                    payment = {
                        "sender_id": sender_id,
                        "timestamp": timestamp,
                        "coverage_end": coverage_end.isoformat(),
                        "message": message
                    }
                    new_payments.append(payment)
    return new_payments

def load_last_timestamp():
    if not os.path.exists(HAPPY_INSURANCE_FILE):
        return 0
    with open(HAPPY_INSURANCE_FILE, "r", encoding="utf-8") as f:
        return int(f.read().strip() or "0")

def save_last_timestamp(timestamp):
    with open(HAPPY_INSURANCE_FILE, "w", encoding="utf-8") as f:
        f.write(str(timestamp))

def save_insurance_logs(new_logs):
    _initialise_log_file()
    with open(HAPPY_INSURANCE_LOG_FILE, "r+", encoding="utf-8") as f:
        existing = json.load(f)
        updated = existing + new_logs
        f.seek(0)
        json.dump(updated, f, indent=2)
        f.truncate()

def load_insurance_logs():
    _initialise_log_file()
    with open(HAPPY_INSURANCE_LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_active_insurance_logs():
    logs = load_insurance_logs()
    now = datetime.now(tz=timezone.utc)
    active = [
        log for log in logs
        if datetime.fromtimestamp(log["timestamp"], tz=timezone.utc) <= now < datetime.fromisoformat(log["coverage_end"])
    ]
    return active

def get_recent_insurance_logs(hours=24):
    logs = load_insurance_logs()
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    recent = [
        log for log in logs
        if datetime.fromtimestamp(log["timestamp"], tz=timezone.utc) >= cutoff
    ]
    return recent

async def post_insurance_to_channel(bot, payment):
    channel = discord.utils.get(bot.get_all_channels(), name="happy-insurance-tracker")
    if not channel:
        print("❌ Channel 'happy-insurance-tracker' not found.")
        return

    dt = datetime.fromtimestamp(payment["timestamp"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    end_dt = datetime.fromisoformat(payment["coverage_end"]).strftime("%Y-%m-%d %H:%M:%S UTC")

    msg = (
        f"🛡️ **New Happy Insurance Payment!**\n"
        f"👤 **Sender ID**: {payment['sender_id']}\n"
        f"⏰ **Time**: {dt}\n"
        f"🕒 **Coverage ends at**: {end_dt}\n"
        f"📝 **Message**: {payment['message'] or '(no message)'}"
    )
    await channel.send(msg)

def initialise_happy_insurance_file():
    if not os.path.exists(HAPPY_INSURANCE_FILE):
        with open(HAPPY_INSURANCE_FILE, "w", encoding="utf-8") as f:
            f.write("0")
        print("✅ Created happy insurance timestamp file.")
