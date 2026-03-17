import os
from dotenv import load_dotenv
from discord_webhook import DiscordWebhook
from slack_sdk.webhook import WebhookClient


load_dotenv()

URL = os.getenv("DISCORD_WEBHOOK")


def send_content_to_discord(content: str) -> None:
    webhook = DiscordWebhook(url=URL, content=content)
    response = webhook.execute()
    if response.status_code in [200, 204]:
        print("Webhook executed successfully with an embed!")
    else:
        print(f"Failed to execute webhook. Status code: {response.status_code}")


def send_content_to_slack(content: str, webhook_url: str = os.getenv("SLACK_WEBHOOK")):
    webhook = WebhookClient(webhook_url)
    response = webhook.send(str(content))

    assert response.status_code == 200
    assert response.body == "ok"
    print("Content Sent Successfully!!")
