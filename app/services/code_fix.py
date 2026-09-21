from app.services.llm import ask_llm


def generate_code_fix(
    issue: dict,
    source_context: str,
    chat_history: list | None = None
):

    if chat_history is None:
        chat_history = []

    file_path = issue.get(
        "file_path",
        "Unknown"
    )

    line_number = issue.get(
        "line_number",
        "Unknown"
    )

    severity = issue.get(
        "severity",
        "Unknown"
    )

    issue_type = issue.get(
        "issue_type",
        "Unknown"
    )

    message = issue.get(
        "message",
        "No description available"
    )

    context = f"""
FILE:
{file_path}

LINE:
{line_number}

SEVERITY:
{severity}

ISSUE TYPE:
{issue_type}

DETECTED ISSUE:
{message}

SOURCE CONTEXT:
{source_context}
"""

    answer = ask_llm(
        question=(
            "Generate a safe and specific code fix suggestion "
            "for this detected issue. Show the current relevant "
            "code and the proposed replacement when possible."
        ),
        context=context,
        chat_history=chat_history
    )

    return {
        "file_path": file_path,
        "line_number": line_number,
        "issue_type": issue_type,
        "suggested_fix": answer
    }