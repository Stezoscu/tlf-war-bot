import os
import time
import json
from datetime import datetime
import numpy as np
import requests
import matplotlib.pyplot as plt
from io import BytesIO
from pathlib import Path

import discord
from discord import app_commands


def predict_war_end(current_hour, current_lead, your_score, starting_score_goal):
    lead_gain_per_hour = current_lead / current_hour
    opponent_score = your_score - current_lead

    hours = np.arange(current_hour, 200, 0.5)
    lead_values = current_lead + lead_gain_per_hour * (hours - current_hour)
    target_values = starting_score_goal * (0.99) ** (hours - 24)

    end_index = np.argmax(lead_values >= target_values)
    end_hour = hours[end_index]
    final_lead = lead_values[end_index]

    opponent_gain_per_hour = (opponent_score + (lead_gain_per_hour * current_hour)) / current_hour - lead_gain_per_hour
    hours_remaining = end_hour - current_hour
    estimated_opponent_final = opponent_score + opponent_gain_per_hour * hours_remaining
    estimated_your_final = estimated_opponent_final + final_lead

    return {
        "war_end_hour": round(end_hour, 1),
        "hours_remaining": round(hours_remaining, 1),
        "your_final_score": int(estimated_your_final),
        "opponent_final_score": int(estimated_opponent_final),
        "final_lead": int(final_lead)
    }


# ---- Torn API fetcher ----
def fetch_v2_war_data():
    api_key = os.getenv("TORN_API_KEY")
    your_faction_id = int(os.getenv("FACTION_ID"))

    url = f"https://api.torn.com/v2/faction/?selections=wars&key={api_key}"
    response = requests.get(url)
    data = response.json()

    ranked_war = data.get("wars", {}).get("ranked")
    if not ranked_war:
        raise ValueError("No ranked war found")

    factions = ranked_war["factions"]
    if len(factions) != 2:
        raise ValueError("Expected exactly 2 factions in war data")

    if factions[0]["id"] == your_faction_id:
        your = factions[0]
        enemy = factions[1]
    else:
        your = factions[1]
        enemy = factions[0]

    start_timestamp = ranked_war["start"]
    current_timestamp = time.time()
    current_hour = round((current_timestamp - start_timestamp) / 3600, 1)

    your_score = your["score"]
    enemy_score = enemy["score"]
    current_lead = your_score - enemy_score
    starting_goal = ranked_war.get("target", 3000)

    return {
        "war_id": ranked_war["war_id"],
        "factions": [your["name"], enemy["name"]],
        "start": start_timestamp,
        "current_hour": current_hour,
        "your_score": your_score,
        "current_lead": current_lead,
        "starting_goal": starting_goal
    }

# ---- Logging helper ----
def log_war_data(data: dict, result: dict):
    log_path = Path("data/current_war.json")
    timestamp = int(datetime.utcnow().timestamp())

    log_entry = {
        "timestamp": timestamp,
        "current_hour": data["current_hour"],
        "your_score": data["your_score"],
        "lead": data["current_lead"],
        "target": data["starting_goal"],
        "predicted_end": result["war_end_hour"]
    }

    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if existing["war_id"] != data["war_id"]:
            # New war, reset log
            log_data = {
                "war_id": data["war_id"],
                "factions": data["factions"],
                "start": data["start"],
                "history": [log_entry]
            }
        else:
            existing["history"].append(log_entry)
            log_data = existing
    else:
        # New file
        log_data = {
            "war_id": data["war_id"],
            "factions": data["factions"],
            "start": data["start"],
            "history": [log_entry]
        }

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=4)

# ---- Manual command ----
