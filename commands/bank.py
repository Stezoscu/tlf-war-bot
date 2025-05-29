import discord
from discord import app_commands
from discord.ext import commands
from utils.bank import update_balance, get_balance, get_all_balances

YOUR_DISCORD_USER_ID = 521438347705450507  # Replace with your Discord ID

@app_commands.command(name="deposit", description="Deposit T$ into someone's Bank of Seb account")
@app_commands.describe(
    user="User to deposit for",
    amount="Amount to deposit"
)
async def deposit(interaction: discord.Interaction, user: discord.User, amount: int):
    if interaction.user.id != YOUR_DISCORD_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
        return

    update_balance(user.id, amount)
    balance = get_balance(user.id)
    await interaction.response.send_message(
        f"💰 Deposited {amount:n} T$ for {user.mention}. New balance: {balance:n} T$"
    )

@app_commands.command(name="withdraw", description="Withdraw T$ from someone's Bank of Seb account (can go negative)")
@app_commands.describe(
    user="User to withdraw from",
    amount="Amount to withdraw"
)
async def withdraw(interaction: discord.Interaction, user: discord.User, amount: int):
    if interaction.user.id != YOUR_DISCORD_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
        return

    # Allow negative balances for loans
    update_balance(user.id, -amount)
    new_balance = get_balance(user.id)
    emoji = "🏧" if new_balance >= 0 else "💸"
    await interaction.response.send_message(
        f"{emoji} Withdrew {amount:n} T$ from {user.mention}. New balance: {new_balance:n} T$"
    )

@app_commands.command(name="check_statement", description="Check your Bank of Seb balance")
async def check_statement(interaction: discord.Interaction):
    balance = get_balance(interaction.user.id)
    emoji = "💰" if balance >= 0 else "💸"
    await interaction.response.send_message(
        f"{emoji} {interaction.user.mention}, your current balance is: {balance:n} T$"
    )

@app_commands.command(name="loan_summary", description="View all Bank of Seb balances")
async def loan_summary(interaction: discord.Interaction):
    from utils.bank import get_all_balances
    if interaction.user.id != YOUR_DISCORD_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    balances = get_all_balances()
    if not balances:
        await interaction.response.send_message("📄 No accounts found.", ephemeral=True)
        return

    lines = []
    for user_id_str, balance in sorted(balances.items(), key=lambda x: int(x[1]), reverse=True):
        user_id = int(user_id_str)
        try:
            user = await interaction.client.fetch_user(user_id)
            name = user.display_name
        except Exception:
            name = f"User {user_id}"
        lines.append(f"- **{name}**: {balance:n} T$")

    summary = "\n".join(lines)
    await interaction.response.send_message(f"📊 **Bank of Seb Balances:**\n{summary}", ephemeral=True)


@app_commands.command(name="bank_adjust", description="Manually adjust a user's Bank of Seb balance")
@app_commands.describe(user="User to adjust", amount="Positive or negative amount to apply")
async def bank_adjust(interaction: discord.Interaction, user: discord.User, amount: int):
    if interaction.user.id != YOUR_DISCORD_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    from utils.bank import update_balance, get_balance
    update_balance(user.id, amount)
    new_balance = get_balance(user.id)

    verb = "credited" if amount >= 0 else "debited"
    await interaction.response.send_message(
        f"🛠️ {verb.capitalize()} {abs(amount):n} T$ for {user.mention}. New balance: {new_balance:n} T$"
    )
