import json
from utils.notifier import send_content_to_discord
from utils.graphs import build_beat_graph
from utils.states import CoreState
from celery import Celery
from dotenv import load_dotenv
import os


load_dotenv()

app = Celery("my_app", broker=os.getenv("CELERY_BROKER_URL"))

app.autodiscover_tasks()


@app.task(name="tasks.send_issues_to_discord")
def send_issues_to_discord():
    print("Sending issues to Discord")
    workflow = build_beat_graph()
    output: CoreState = workflow.invoke(
        {
            "user_goal": "To start with Open Source and long term contributions.",
            "user_stack": "Python,django,Celery,Langchain,Langgraph,Sklearn",
        }
    )
    if output.get("error"):
        send_content_to_discord(f"⚠️ Pipeline failed: {output['error']}")
    else:
        formatted = json.dumps(
            [s.model_dump() for s in output["scored_issues"]], indent=2, default=str
        )
        send_content_to_discord(formatted)


app.conf.beat_schedule = {
    "find_issues": {
        "task": "tasks.send_issues_to_discord",
        "schedule": 86400,
    },
}
