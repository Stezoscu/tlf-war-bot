import discord
from discord import app_commands
from discord.ext import commands
from utils.bank import update_balance, get_balance

YOUR_DISCORD_USER_ID = 521438347705450507  # Replace with your actual ID

@app_commands.command(name="deposit", description="Deposit T$ into someone's Bank of Seb account")
@app_commands.describe(user="User to deposit for", amount="Amount to deposit")
async def deposit(interaction: discord.Interaction, user: discord.User, amount: int):
    if interaction.user.id != YOUR_DISCORD_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
        return

    update_balance(user.id, amount)
    balance = get_balance(user.id)
    await interaction.response.send_message(f"💰 Deposited {amount:n} T$ for {user.mention}. New balance: {balance:n} T$")

@app_commands.command(name="withdraw", description="Withdraw T$ from someone's Bank of Seb account")
@app_commands.describe(user="User to withdraw from", amount="Amount to withdraw")
async def withdraw(interaction: discord.Interaction, user: discord.User, amount: int):
    if interaction.user.id != YOUR_DISCORD_USER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
        return

    current_balance = get_balance(user.id)
    if amount > current_balance:
        await interaction.response.send_message(f"❌ {user.mention} does not have enough T$ ({current_balance:n}).", ephemeral=True)
        return

    update_balance(user.id, -amount)
    new_balance = get_balance(user.id)
    await interaction.response.send_message(f"🏧 Withdrew {amount:n} T$ from {user.mention}. New balance: {new_balance:n} T$")

@app_commands.command(name="check_statement", description="Check your Bank of Seb balance")
async def check_statement(interaction: discord.Interaction):
    balance = get_balance(interaction.user.id)
    await interaction.response.send_message(f"📄 {interaction.user.mention}, your current balance is: {balance:n} T$")
