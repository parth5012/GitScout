from dotenv import load_dotenv
import os
import requests


load_dotenv()

def get_device_code():
    client_id = os.getenv('GITHUB_CLIENT_ID')
    if client_id:
        pass