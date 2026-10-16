from app.services.llm import ask_llm
from app.services.source_context import get_source_context


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

        file_path = issue.get(
            "file_path",
            "Unknown"
        )

        line_number = issue.get(
            "line_number",
            0
        )

        source_context = ""

        if (
            file_path != "Unknown"
            and isinstance(
                line_number,
                int
            )
            and line_number > 0
        ):

            source_context = get_source_context(
                file_path=file_path,
                line_number=line_number,
                context_lines=3
            )

        if not source_context:

            source_context = (
                "Source context is not available."
            )

        issue_context_parts.append(
            f"""
Issue {index}

File:
{file_path}

Line:
{line_number}

Severity:
{issue.get("severity", "Unknown")}

Issue Type:
{issue.get("issue_type", "Unknown")}

Detected Message:
{issue.get("message", "No description available")}

Actual Source Context:
{source_context}
"""
        )

    issue_context = "\n".join(
        issue_context_parts
    )

    answer = ask_llm(
        question=(
            "Provide practical and source-specific "
            "improvement suggestions for the detected "
            "code issues."
        ),
        context=issue_context,
        chat_history=chat_history
    )

    return {
        "total_issues": len(issues),
        "improvements": answer
    }