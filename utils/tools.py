from langchain.tools import tool
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
import io
import os
import requests
from zipfile import ZipFile
from typing import List, Dict
from utils.models import IssueScore
from utils.parsers import parser1
from utils.helpers import (
    get_github_client,
    get_repo_from_url,
    process_issues,
    get_secondary_llm
)
from utils.prompts import likelihood_score_prompt


@tool
def fetch_issues(query: str) -> Dict:
    """
    Searches GitHub for open, unassigned issues based on a specific query string.

    Use this tool after generating a precise query string. It returns a processed
    collection of issues including titles, descriptions, and metadata.

    Args:
        query: A valid GitHub search API query string (e.g., 'label:"good first issue" language:python').

    Returns:
        A dictionary containing a list of processed issue objects and total count.
    """
    try:
        client = get_github_client()
        issues = client.search_issues(query=query, sort="created", order="desc")
        print(f"Found {issues.totalCount} matching issues!")
        issues = process_issues(issues=issues)
        return issues
    except Exception as e:
        return {"error": str(e), "issues": []}
    finally:
        client.close()


@tool
def generate_github_query(user_goal: str, user_stack: str) -> str:
    """Transforms a user's high-level goal and technical stack into a structured GitHub search query string.
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
    return response.content


@tool
def get_likelihood_score(skill_set: str, metadata: List[Dict]) -> List[IssueScore]:
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
    llm = get_secondary_llm()
    chain = likelihood_score_prompt | llm | parser1
    response = chain.invoke({"skill_set": skill_set, "metadata": metadata})
    if response.scores:
        return list(response.scores)
    return []


@tool
def fetch_codebase(url: str):
    """
    Fetch the codebase of any public github repository, helps in in-depth analysis of codebase when needed.
    :param url: the url of github repository.
    :type url: str
    """
    try:
        with get_repo_from_url(url) as repo:
            archive_url = repo.get_archive_link("zipball")  # client is still open ✅
        response = requests.get(archive_url)  # no client needed here, just HTTP
        path = f"{os.path.dirname(os.path.abspath(__file__))}/codebases"
        with ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(path)
        return f"Success, CodeBase is now accessible at {path}"
    except Exception as e:
        return f"Failure, Reason: {e}"


@tool
def map_universal_architecture(repo_path: str) -> dict:
    """
    Scans a local repository and returns the file structure for multiple languages
    (Python, JS, TS, Go, Rust, etc.). It extracts Class and Function names.
    Use this to understand the current capabilities of the codebase.
    """
    architecture = {}

    # We define the extensions we want GitScout to care about
    supported_extensions = [".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp"]

    # LangChain's GenericLoader walks the directory for us
    loader = GenericLoader.from_filesystem(
        repo_path,
        glob="**/*",
        suffixes=supported_extensions,
        # LanguageParser automatically uses Tree-sitter to parse the code syntax
        parser=LanguageParser(),
    )

    # This returns a list of "Documents". LangChain automatically splits the files
    # so that each Document represents a single Function or Class!
    docs = loader.load()

    for doc in docs:
        # Get the relative file path
        source_file = os.path.relpath(doc.metadata["source"], repo_path)

        # LangChain tags the metadata with 'content_type' (e.g., 'functions_classes')
        # We can use this to build our skeleton
        if source_file not in architecture:
            architecture[source_file] = {"components": []}

        # We don't want the actual code, just the signature/definition
        # We can grab the first line of the chunk (which is usually the 'def' or 'class' declaration)
        first_line = doc.page_content.split("\n")[0].strip()

        # Avoid adding the "leftover" code chunks that aren't functions/classes
        if doc.metadata.get("content_type") == "functions_classes":
            architecture[source_file]["components"].append(first_line)

    return architecture


@tool
def read_file_content(repo_path: str, file_path: str) -> str:
    """
    Reads the full content of a specific file from a locally extracted repo.
    Use after map_universal_architecture to drill into a specific file.

    Args:
        repo_path: Path to the extracted repo root (e.g. './codebases/myrepo')
        file_path: Relative path to the file (e.g. 'src/auth/login.py')
    """
    full_path = os.path.join(repo_path, file_path)
    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


tools = [
    fetch_issues,
    generate_github_query,
    get_likelihood_score,
    fetch_codebase,
    map_universal_architecture,
    read_file_content,
]
