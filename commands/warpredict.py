# commands/warpredict.py

import discord
from discord import app_commands
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import time
from datetime import timedelta

from utils.predictor import predict_war_end, fetch_v2_war_data, log_war_data, estimate_win_time_if_no_more_hits


@app_commands.command(name="warpredict", description="Predict war outcome from manual inputs.")
@app_commands.describe(
    current_hour="Current hour of the war (e.g., 36.5)",
    current_lead="Current lead in the war (positive or negative number)",
    your_score="Your current total score",
    starting_goal="The original target score (usually 3000)"
)
async def warpredict(interaction: discord.Interaction, current_hour: float, current_lead: int, your_score: int, starting_goal: int):
    await interaction.response.defer(thinking=True, ephemeral=True)

    result = predict_war_end(current_hour, current_lead, your_score, starting_goal)

    pseudo_data = {
        "war_id": 0,
        "factions": ["Manual Input", "Manual Input"],
        "start": int(time.time()) - int(current_hour * 3600),
        "current_hour": current_hour,
        "your_score": your_score,
        "current_lead": current_lead,
        "starting_goal": starting_goal
    }
    log_war_data(pseudo_data, result)

    no_more_hits_msg = estimate_win_time_if_no_more_hits(current_lead, starting_goal, current_hour)

    await interaction.followup.send(
        f"🧠 **TLF Torn War Predictor**\n"
        f"📅 War ends at hour **{result['war_end_hour']}** (in {result['hours_remaining']}h)\n"
        f"🏁 Final Scores:\n"
        f" - You: **{result['your_final_score']}**\n"
        f" - Opponent: **{result['opponent_final_score']}**\n"
        f"📊 Final Lead: **{result['final_lead']}**\n"
        f"{no_more_hits_msg}"
    )

@app_commands.command(name="autopredict", description="Auto predict war outcome using live Torn API data.")
@app_commands.describe(
    starting_goal="The original target score (override if known)"
)
async def autopredict(interaction: discord.Interaction, starting_goal: int = None):
    await interaction.response.defer(thinking=True)  # Let Discord know we're working!

    try:
        data = fetch_v2_war_data()
        current_hour = data["current_hour"]

        # Step 1: Decide current target and starting goal logic
        if starting_goal:
            decay_hours = max(0, int(current_hour) - 24)
            current_target = starting_goal * (0.99 ** decay_hours)
            inferred_goal_text = "(override used)"
        else:
            current_target = data.get("current_target")
            if current_target is None:
                raise ValueError("No current target available to infer starting goal.")
            decay_hours = max(0, int(current_hour) - 24)
            inferred_starting_goal = current_target / (0.99 ** decay_hours)
            starting_goal = inferred_starting_goal
            inferred_goal_text = f"(inferred original target ≈ {int(inferred_starting_goal)})"

        data["starting_goal"] = starting_goal

        # Step 2: Run prediction
        result = predict_war_end(
            data["current_hour"],
            data["current_lead"],
            data["your_score"],
            data["starting_goal"]
        )
        log_war_data(data, result)

        # Step 3: No-more-hits estimate
        no_more_hits_msg = estimate_win_time_if_no_more_hits(
            data["current_lead"], starting_goal, current_hour
        )

        # Step 4: Chart generation
        hours = np.arange(data["current_hour"], result["war_end_hour"] + 1, 0.5)
        lead_gain_per_hour = data["current_lead"] / data["current_hour"] if data["current_hour"] != 0 else 0
        lead_values = data["current_lead"] + lead_gain_per_hour * (hours - data["current_hour"])
        target_values = data["starting_goal"] * (0.99 ** (hours - 24))

        fig, ax = plt.subplots()
        ax.plot(hours, lead_values, label="Your Lead")
        ax.plot(hours, target_values, label="Target", linestyle="--")
        ax.axvline(result["war_end_hour"], color="red", linestyle=":", label="Predicted End")
        ax.set_title("Lead vs. Decaying Target")
        ax.set_xlabel("War Hour")
        ax.set_ylabel("Points")
        ax.legend()
        ax.grid(True)

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        file = discord.File(fp=buf, filename="prediction_chart.png")
        plt.close()

        await interaction.followup.send(
            content=(
                f"📡 **Auto Prediction Based on Live Torn Data**\n"
                f"🕓 War Duration: **{current_hour} hours**\n"
                f"📊 Current Score: **{data['your_score']}** | Lead: **{data['current_lead']}**\n"
                f"🎯 Current Target: **{int(current_target)}** {inferred_goal_text}\n"
                f"📅 Predicted End at hour **{result['war_end_hour']}** (i.e. in **{result['hours_remaining']}h**)\n"
                f"🏁 Final Score Estimate:\n"
                f" - You: **{result['your_final_score']}**\n"
                f" - Opponent: **{result['opponent_final_score']}**\n"
                f"{no_more_hits_msg}"
            ),
            file=file
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")
