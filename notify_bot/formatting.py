import re


_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!"


def escape_md2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    return re.sub(r"([" + re.escape(_ESCAPE_CHARS) + r"])", r"\\\1", text)


_STATUS_EMOJI = {
    "success": "\u2705",
    "failure": "\u274c",
    "info": "\u2139\ufe0f",
}


def format_report(
    title: str,
    status: str,
    summary: str,
    details: list[str] | None = None,
    duration: str | None = None,
) -> str:
    """Format a structured report into Telegram MarkdownV2."""
    emoji = _STATUS_EMOJI.get(status, "\u2139\ufe0f")
    lines: list[str] = []

    lines.append(f"{emoji} *{escape_md2(title)}*")
    lines.append("")
    lines.append(escape_md2(summary))

    if details:
        lines.append("")
        for item in details:
            lines.append(f"\u2022 {escape_md2(item)}")

    if duration:
        lines.append("")
        lines.append(f"\u23f1 {escape_md2(duration)}")

    return "\n".join(lines)
