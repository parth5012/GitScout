from langgraph.graph import StateGraph, END
from langgraph.prebuilt import tools_condition
from utils.nodes import (
    chat_node,
    fetch_issues,
    generate_github_query,
    get_likelihood_score,
    tool_node,
    send_issues_to_discord,
)
from .states import CoreState, FilterAgentState


def get_filter_agent():
    """
    Used for Filtering out Open Source repos based on metrics like Star to Issues Ratio,Maintainer Responsiveness and Issue difficulty.
    """
    graph = StateGraph(state_schema=FilterAgentState)


def get_semantic_matcher():
    """
    Used to match the given skillset with the selected issue.
    """
    pass


def build_core_graph():
    graph = StateGraph(state_schema=CoreState)
    graph.add_node("chat_node", chat_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("chat_node")
    graph.add_conditional_edges("chat_node", tools_condition)
    graph.add_edge("tools", "chat_node")

    workflow = graph.compile()
    return workflow


def build_beat_graph():
    graph = StateGraph(state_schema=CoreState)
    graph.add_node("generate_query", generate_github_query)
    graph.add_node("fetch_issues", fetch_issues)
    graph.add_node("get_likelihood_score", get_likelihood_score)
    graph.add_node("send_issues_to_discord", send_issues_to_discord)

    graph.set_entry_point("generate_query")
    graph.add_edge("generate_query", "fetch_issues")
    graph.add_edge("fetch_issues", "get_likelihood_score")
    graph.add_edge("get_likelihood_score", "send_issues_to_discord")
    graph.add_edge("send_issues_to_discord", END)

    return graph.compile()
