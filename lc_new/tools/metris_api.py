# tools/metris_api.py
import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

METRIS_URI = os.getenv("METRIS_URI")
METRIS_USERNAME = os.getenv("METRIS_USERNAME")
METRIS_PASSWORD = os.getenv("METRIS_PASSWORD")
REQUEST_VERIFY = os.getenv("REQUEST_VERIFY", "false").lower() == "true"
DEFAULT_TIMEOUT = 25

def _now_utc():
    return datetime.now(timezone.utc)

def get_metris_token():
    resp = requests.post(
        f"{METRIS_URI}/api/account/authenticate",
        json={"username": METRIS_USERNAME, "password": METRIS_PASSWORD},
        verify=REQUEST_VERIFY,
        timeout=DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    token = resp.json().get("id")
    return {"Authorization": f"Bearer {token}"}

def get_tag_values(tag_id: int):
    headers = get_metris_token()
    resp = requests.get(
        f"{METRIS_URI}/api/historian/v02/tagvalues",
        headers=headers,
        params={"ids": [tag_id]},
        timeout=DEFAULT_TIMEOUT,
        verify=REQUEST_VERIFY,
    )
    resp.raise_for_status()
    return resp.json()

def get_trend_values(tag_id: int, days: int = 7):
    headers = get_metris_token()
    end = _now_utc()
    start = end - timedelta(days=days)

    resp = requests.get(
        f"{METRIS_URI}/api/historian/v02/trendvalues",
        headers=headers,
        params={
            "tagid": tag_id,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "interpolationresolution": 1008,
        },
        timeout=DEFAULT_TIMEOUT,
        verify=REQUEST_VERIFY,
    )
    resp.raise_for_status()
    return resp.json()
