from utils.tracked_items import load_tracked_items

def normalise_item_name(name: str) -> str:
    tracked_items = load_tracked_items()
    for display_name, internal_key in tracked_items.items():
        if name.lower().strip() == display_name.lower() or name.lower().strip() == internal_key:
            return internal_key
    return None
