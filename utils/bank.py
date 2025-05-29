import os
import json

BANK_FILE = "/mnt/data/bank_of_seb.json"

def initialise_bank_file():
    """Create the bank file if it doesn't exist."""
    if not os.path.exists(BANK_FILE):
        print("🆕 Creating empty bank file...")
        with open(BANK_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        print("✅ Bank file created.")
    else:
        print("✅ Bank file already exists.")

def load_bank_data():
    if not os.path.exists(BANK_FILE):
        return {}
    with open(BANK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_bank_data(data):
    with open(BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_balance(user_id: int) -> int:
    data = load_bank_data()
    return data.get(str(user_id), 0)

def update_balance(user_id: int, amount: int):
    data = load_bank_data()
    uid = str(user_id)
    data[uid] = data.get(uid, 0) + amount
    save_bank_data(data)

def get_all_balances() -> dict:
    """Return the full dict of user_id -> balance."""
    return load_bank_data()
