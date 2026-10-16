from dotenv import load_dotenv
from langchain_groq import ChatGroq


load_dotenv()


llm = ChatGroq(
    model="qwen/qwen3.8-27b",
    temperature=0,
    max_tokens=1200,
    reasoning_effort="none"
)


def ask_llm(
    question: str,
    context: str,
    chat_history: list
):

    conversation = ""

    for message in chat_history:

        role = message.get("role", "")
        content = message.get("content", "")

        if content:

            conversation += (
                f"{role}: {content}\n"
            )

    prompt = f"""
You are an AI Codebase Assistant.

Your job is to help the user understand the provided software
codebase accurately and clearly.

Answer the user's current question using:
1. The provided code context.
2. The previous conversation when relevant.

IMPORTANT RULES:

- Answer only from the provided code context and conversation.
- Do not invent files, functions, classes, routes, libraries,
  or implementation details.
- If the provided context does not contain enough information,
  clearly say that the information is not available in the
  provided code context.
- Understand follow-up references such as "it", "this", "that",
  "there", and "this line" using the previous conversation.
- Do not repeat the entire code context.
- Mention the relevant file name when it helps the user
  understand where the implementation exists.
- When showing a code line, format it using backticks.
- Keep answers focused on the user's question.

RESPONSE STYLE:

- For simple factual questions, give a short but useful answer
  with one or two supporting details.
- For explanation or "how does it work" questions, provide a
  clear explanation in around 2 to 5 sentences.
- For implementation questions, explain what the relevant code
  does and how it works.
- If multiple related components are involved, explain their
  relationship briefly.
- Use a small bullet list when it improves readability.
- Do not make every answer unnecessarily long.
- The answer should be detailed enough for a developer to
  understand the implementation without reading the entire
  codebase.

PREVIOUS CONVERSATION:
{conversation}

CODE CONTEXT:
{context}

CURRENT USER QUESTION:
{question}

FINAL ANSWER:
"""

    response = llm.invoke(
        prompt
    )

    content = response.content

    if not isinstance(content, str):

        content = str(content)

    content = content.strip()

    if not content:

        return (
            "I could not generate an answer "
            "from the provided code context."
        )

    return content


def explain_file(
    file_path: str,
    extension: str,
    content: str
):

    prompt = f"""
You are an AI Codebase Assistant.

Explain the provided source code file accurately based only
on the file content given below.

FILE INFORMATION:

File: {file_path}
Extension: {extension}

CODE:

{content}

IMPORTANT RULES:

- Use only the provided file content.
- Do not invent functionality that is not present in the file.
- Do not assume the purpose of missing or unseen files.
- Do not claim that a library, function, class, route, database,
  or feature exists unless it is visible in the provided code.
- If something cannot be determined from this file, clearly
  state that it cannot be determined from the provided file.
- Do not reproduce the entire source code.
- Mention important functions, classes, routes, imports,
  configuration, or application logic when they are present.
- Keep the explanation technically accurate and developer-friendly.

STRUCTURE THE RESPONSE AS:

Purpose:
Briefly explain what this file does.

Key Components:
List the important components found in the file.

How It Works:
Explain the main execution or processing flow.

Important Details:
Mention relevant frameworks, libraries, database connections,
routes, configuration, or other significant implementation
details that are actually present.

Keep the explanation concise but sufficiently detailed for a
developer to understand the role of this file.

FINAL ANSWER:
"""

    response = llm.invoke(
        prompt
    )

    explanation = response.content

    if not isinstance(explanation, str):

        explanation = str(explanation)

    explanation = explanation.strip()

    if not explanation:

        return (
            "I could not generate an explanation "
            "from the provided file."
        )

    return explanation