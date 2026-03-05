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
    print(output)

app.conf.beat_schedule = {
    "find_issues": {
        "task": "tasks.send_issues_to_discord",
        "schedule": 86400,
    },
}
