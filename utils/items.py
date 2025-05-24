import os
import requests


def fetch_item_market_price(item_id: str):
    """
    Fetches the lowest item market listing for the given item ID from Torn API v2.
    Returns a tuple: (price: int, quantity: int), or (None, None) if no listings found.
    """
    api_key = os.getenv("TORN_API_KEY")
    if not api_key:
        raise RuntimeError("TORN_API_KEY not set in environment variables")

    url = f"https://api.torn.com/v2/market/{item_id}/itemmarket?key={api_key}"
    response = requests.get(url)
    data = response.json()

    listings = data.get("itemmarket", {}).get("listings", [])
    if listings:
        # Find the listing with the lowest price
        lowest = min(listings, key=lambda l: l["price"])
        return lowest["price"], lowest["amount"]

    return None, None

def normalise_item_name(name: str) -> str:
    return name.lower().replace(" ", "_")