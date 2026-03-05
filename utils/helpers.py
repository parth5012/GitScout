from typing import List
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.language_models.llms import LLM
from contextlib import contextmanager
import os
from dotenv import load_dotenv
from github import Github
from github.Auth import Token


load_dotenv()


def create_embeddings():
    pass


def store_embeddings():
    pass


llm_choice = os.getenv("LLM_PROVIDER")


def get_chat_llm() -> LLM:
    if llm_choice == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key)
    else:
        api_key = os.getenv("GROQ_API_KEY")
        return ChatGroq(model="qwen/qwen3-32b")


def get_secondary_llm() -> LLM:
    if llm_choice == "google":
        api_key = os.getenv("GROQ_API_KEY")
        return ChatGroq(model="qwen/qwen3-32b")
    else:
        api_key = os.getenv("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key)


def get_github_client() -> Github:
    access_token = Token(os.getenv("GITHUB_TOKEN"))
    client = Github(auth=access_token)
    return client


def process_issues(issues):
    issue_data = []
    for issue in issues[:10]:
        repo = issue.repository

        issue_dict = {
            "title": issue.title,
            "url": issue.html_url,
            "repo_name": repo.full_name,
            "stars": repo.stargazers_count,
            "labels": [label.name for label in issue.labels],
            "created_at": issue.created_at,
            "comments_count": issue.comments,
        }

        issue_data.append(issue_dict)
        print(f"[{issue_dict['repo_name']}] {issue_dict['title']}")

    return issue_data


def get_repo_identifier(url: str) -> str:
    keywords: List = url.split("/")
    username = keywords[-2]
    repo_name = keywords[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    print(username, repo_name)
    return f"{username}/{repo_name}"


@contextmanager
def get_repo_from_url(url: str):
    g = get_github_client()
    try:
        repo_identifier = get_repo_identifier(url)
        yield g.get_repo(repo_identifier)  # repo is alive inside the `with` block
    finally:
        g.close()  # always closes, even on exception
