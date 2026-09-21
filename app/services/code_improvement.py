from app.services.llm import ask_llm


def generate_code_improvements(
    issues: list,
    chat_history: list | None = None
):

    if not issues:

        return {
            "total_issues": 0,
            "improvements": []
        }

    if chat_history is None:
        chat_history = []

    issue_context_parts = []

    for index, issue in enumerate(
        issues,
        start=1
    ):

        issue_context_parts.append(
            f"""
Issue {index}

File:
{issue.get("file_path", "Unknown")}

Line:
{issue.get("line_number", "Unknown")}

Severity:
{issue.get("severity", "Unknown")}

Issue Type:
{issue.get("issue_type", "Unknown")}

Message:
{issue.get("message", "No description available")}
"""
        )

    issue_context = "\n".join(
        issue_context_parts
    )

    answer = ask_llm(
        question=(
            "Provide practical improvement suggestions "
            "for the detected code issues."
        ),
        context=issue_context,
        chat_history=chat_history
    )

    return {
        "total_issues": len(issues),
        "improvements": answer
    }
