from app.keys import OFFLINE_API_KEYS

def validate_key(api_key: str) -> bool:
    return api_key in OFFLINE_API_KEYS.values()

