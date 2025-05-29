from utils.tracked_items import load_combined_items_data


def normalise_item_name(name: str) -> str:
    """Resolve item name or ID to its internal key (case-insensitive)."""
    items = load_combined_items_data()
    for display_name, data in items.items():
        if name.lower().strip() == display_name.lower() or name.lower().strip() == str(data.get("item_id")):
            return display_name
    return name.strip()
