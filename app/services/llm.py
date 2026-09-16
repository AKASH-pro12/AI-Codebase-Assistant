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

RULES:

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

STYLE:

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