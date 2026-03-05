from typing import Dict, List
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage
from utils.models import IssueScore
from utils.tools import tools
from utils.helpers import get_chat_llm,get_secondary_llm
from utils.states import CoreState
from utils.prompts import SYSTEM_PROMPT
from utils.parsers import parser1
from utils.helpers import get_github_client, process_issues
from utils.prompts import likelihood_score_prompt
from utils.notifier import send_content_to_discord
import json


def chat_node(state: CoreState):
    llm = get_chat_llm()
    messages = state["messages"]
    prompted_messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    llm = llm.bind_tools(tools)
    response = llm.invoke(prompted_messages)
    return {"messages": [response]}


tool_node = ToolNode(tools)


def get_likelihood_score(state: CoreState) -> List[IssueScore]:
    """
    Evaluates the compatibility between a user's skills and a specific GitHub issue.

    This tool uses an LLM to calculate a numerical score (0-100) representing how
    likely the user is to successfully resolve the issue based on the provided
    issue metadata and their skill set.

    Args:
        skill_set: A string describing the user's technical expertise and experience level.
        metadata: A list of dictionaries containing issue details (title, body, labels).

    Returns:
        An integer from 0 to 10, where 10 indicates a perfect match.
    """
    if state.get("error"):  # ← short-circuit if fetch_issues failed
        print(f"Skipping scoring due to earlier error: {state['error']}")
        return {"scored_issues": []}
    skill_set = state["user_stack"]
    metadata = state["issues"]
    llm = get_secondary_llm()
    chain = likelihood_score_prompt | llm | parser1
    response = chain.invoke({"skill_set": skill_set, "metadata": metadata})
    if response.scores:
        return {"scored_issues": list(response.scores)}

    return {"scored_issues": []}


def fetch_issues(state: CoreState) -> Dict:
    """
    Searches GitHub for open, unassigned issues based on a specific query string.

    Use this tool after generating a precise query string. It returns a processed
    collection of issues including titles, descriptions, and metadata.

    Args:
        query: A valid GitHub search API query string (e.g., 'label:"good first issue" language:python').

    Returns:
        A dictionary containing a list of processed issue objects and total count.
    """
    client = None
    try:
        query = state["query"]
        client = get_github_client()
        issues = client.search_issues(query=query, sort="created", order="desc")
        print(f"Found {issues.totalCount} matching issues!")
        issues = process_issues(issues=issues)
        return {"issues": issues}
    except Exception as e:
        return {"error": str(e), "issues": []}
    finally:
        if client:
            client.close()


def generate_github_query(state: CoreState) -> str:
    user_goal = state["user_goal"]
    user_stack = state["user_stack"]
    """
    Transforms a user's high-level goal and technical stack into a structured GitHub search query string.
    It is a mandatory step before calling the fetch_issues tool.

    Args:
        user_goal: The specific type of contribution the user wants to make (e.g., 'bug fixes', 'documentation').
        user_stack: The programming languages or frameworks the user is proficient in (e.g., 'Python, Flask').

    Returns:
        A raw GitHub search string formatted with filters like 'state:open', 'no:assignee', and 'language:'.
    """

    prompt = f"""
    You are an expert GitHub Scout. Your job is to create the PERFECT GitHub search query string.
    
    User Goal: {user_goal}
    User Tech Stack: {user_stack}
    
    Rules for the query:
    1. Always filter for 'state:open'.
    2. Always filter for 'no:assignee' (we want available issues).
    3. Use 'language:X' based on the stack.
    4. If they want beginner issues, use label:"good first issue" OR label:"help wanted".
    5. Return ONLY the raw query string. No markdown, no explanations.
    """
    llm = get_secondary_llm()
    response = llm.invoke(prompt)
    return {"query": response.content}


def send_issues_to_discord(state: CoreState):
    if state.get("error"):
        send_content_to_discord(f"⚠️ Pipeline failed: {state['error']}")
    else:
        formatted = json.dumps(
            [s.model_dump() for s in state["scored_issues"]], indent=2, default=str
        )
        send_content_to_discord(formatted)
