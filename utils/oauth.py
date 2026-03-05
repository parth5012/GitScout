import time
from typing import Dict
from dotenv import load_dotenv
import os
import requests
import webbrowser


load_dotenv()

USER_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"


def get_user_code(client_id) -> Dict:
    try:
        response = requests.post(USER_CODE_URL, params={"client_id": client_id})
        data = response.json()
        return data
    except Exception as e:
        return {"error": str(e)}


def prompt_user_to_authorize():
    data = get_user_code()
    code, uri = data.get("user_code"), data.get("verification_uri")
    print(f"Go to this URL: {uri}")
    print(f"And enter the code: {code}")
    print("redirecting in 15s")
    time.sleep(15)
    webbrowser.open(uri, new=0)


def poll_requests_for_access_token(data, client_id):
    while True:
        time.sleep(data["interval"])
        poll_payload = {
            "client_id": client_id,
            "device_code": data["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }
        poll_response = requests.post(
            TOKEN_URL, data=poll_payload, headers={"Accept": "application/json"}
        )
        poll_data = poll_response.json()

        if "access_token" in poll_data:
            access_token = poll_data["access_token"]
            print("Authorization successful! Access Token:", access_token)
            break
        elif poll_data["error"] == "authorization_pending":
            print("Waiting for user authorization...")
        elif poll_data["error"] == "slow_down":
            # Increase interval if requested
            data["interval"] += 1
            print("Slow down request received, increasing interval.")
        elif poll_data["error"] == "access_denied":
            print("User denied access.")
            break
        elif poll_data["error"] == "expired_token":
            print("Token expired.")
            break
        else:
            print("Unknown error:", poll_data["error"])
            break
