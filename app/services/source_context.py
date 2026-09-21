def get_source_context(
    file_path: str,
    line_number: int,
    context_lines: int = 3
):

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            lines = file.readlines()

    except (
        UnicodeDecodeError,
        OSError
    ):

        return ""

    if not lines:
        return ""

    target_index = line_number - 1

    if target_index < 0:
        target_index = 0

    if target_index >= len(lines):
        target_index = len(lines) - 1

    start_index = max(
        0,
        target_index - context_lines
    )

    end_index = min(
        len(lines),
        target_index + context_lines + 1
    )

    context_parts = []

    for index in range(
        start_index,
        end_index
    ):

        current_line_number = index + 1

        line_content = lines[index].rstrip(
            "\n"
        )

        marker = ">>" if (
            current_line_number == line_number
        ) else "  "

        context_parts.append(
            f"{marker} {current_line_number}: "
            f"{line_content}"
        )

    return "\n".join(
        context_parts
    )