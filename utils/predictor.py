import os
import time
import json
from datetime import datetime
import numpy as np
import requests
import matplotlib.pyplot as plt
from io import BytesIO
from pathlib import Path
from datetime import timedelta
import math

import discord
from discord import app_commands



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

    current_target = ranked_war.get("target", 3000)  # ✅ Already-decayed target

    return {
        "war_id": ranked_war["war_id"],
        "factions": [your["name"], enemy["name"]],
        "start": start_timestamp,
        "current_hour": current_hour,
        "your_score": your_score,
        "current_lead": current_lead,
        "current_target": current_target  # ✅ label clearly
    }

def predict_war_end(current_hour, current_lead, your_score, starting_score_goal):
    lead_gain_per_hour = current_lead / current_hour if current_hour != 0 else 0
    opponent_score = your_score - current_lead
    hours = np.arange(current_hour, 200, 0.5)
    target_values = starting_score_goal * (0.99) ** (hours - 24)

    if current_lead >= 0:
        # We are winning
        lead_values = current_lead + lead_gain_per_hour * (hours - current_hour)
        end_index = np.argmax(lead_values >= target_values)
    else:
        # We are losing
        # Track how far *behind* we are and simulate that worsening
        loss_gap = abs(current_lead)
        loss_increase_per_hour = loss_gap / current_hour if current_hour != 0 else 0
        loss_values = loss_gap + loss_increase_per_hour * (hours - current_hour)
        end_index = np.argmax(loss_values >= target_values)
        # For consistency, treat final_lead as negative
        lead_values = -loss_values

    if end_index == 0 and all(lead_values < target_values):
        raise ValueError("❌ Could not estimate war end — progress too slow.")

    end_hour = hours[end_index]
    final_lead = lead_values[end_index]
    hours_remaining = end_hour - current_hour

    opponent_gain_per_hour = (opponent_score + (lead_gain_per_hour * current_hour)) / current_hour - lead_gain_per_hour
    estimated_opponent_final = opponent_score + opponent_gain_per_hour * hours_remaining
    estimated_your_final = estimated_opponent_final + final_lead

    return {
        "war_end_hour": round(end_hour, 1),
        "hours_remaining": round(hours_remaining, 1),
        "your_final_score": int(estimated_your_final),
        "opponent_final_score": int(estimated_opponent_final),
        "final_lead": int(final_lead)
    }

def estimate_win_time_if_no_more_hits(current_lead: float, starting_goal: float, current_hour: float) -> str:
    """
    Estimate when the decaying target drops below the absolute value of the current lead,
    assuming no more hits are made.
    """
    from math import floor

    if current_lead == 0:
        return "⚖️ The lead is currently zero — unclear when decay will settle the score."

    abs_lead = abs(current_lead)
    decay_hour = floor(current_hour)
    target = starting_goal * (0.99 ** max(0, decay_hour - 24))
    
    while target > abs_lead:
        decay_hour += 1
        if decay_hour - current_hour > 1000:
            return "❌ Unable to estimate (lead too low or error in logic)"
        target *= 0.99

    hours_until_end = decay_hour - current_hour
    from datetime import timedelta
    eta = timedelta(hours=hours_until_end)
    return f"⏳ If no more hits are made, the war will end in {eta} (at hour {decay_hour})."

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



#work out the starting goal from the current target and current hour
def infer_starting_goal(current_target: float, current_hour: float) -> float:
    """
    Infer the original starting goal based on current decayed target and war hour.
    Torn decay begins at hour 25 and reduces the target by 1% each full hour.
    """
    if current_hour < 25:
        return current_target  # No decay yet

    decay_hours = math.floor(current_hour) - 24
    starting_goal = current_target / (0.99 ** decay_hours)
    return round(starting_goal)