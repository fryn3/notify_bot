#!/usr/bin/env python3
"""Standalone CLI for sending Telegram notifications via ntfy.

Calls Telegram API directly — no server dependency.

Usage:
    ntfy "Build completed"
    ntfy --md "**Build** _passed_ on `main`"
    ntfy --report --title "Agent Run" --status success --summary "Refactored auth"
    echo "Deploy finished" | ntfy --raw
    history | ntfy
    history | ntfy --header history
    docker logs app | ntfy -n 10
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)

TELEGRAM_API = "https://api.telegram.org"
_MAX_TG_LENGTH = 4096


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} environment variable is required", file=sys.stderr)
        sys.exit(1)
    return value


def _truncate(text: str, limit: int = _MAX_TG_LENGTH) -> str:
    if len(text) <= limit:
        return text
    marker = "[truncated]\n"
    return marker + text[-(limit - len(marker)):]


def _send_message(token: str, chat_id: str, text: str, parse_mode: str | None = None) -> None:
    text = _truncate(text)

    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload: dict = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    proxy = os.environ.get("PROXY")
    resp = httpx.post(url, json=payload, timeout=30, proxy=proxy)
    data = resp.json()

    if not data.get("ok"):
        desc = data.get("description", "Unknown error")
        print(f"Telegram API error: {desc}", file=sys.stderr)
        sys.exit(1)


_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!"
_STATUS_EMOJI = {"success": "\u2705", "failure": "\u274c", "info": "\u2139\ufe0f"}


def _escape_md2(text: str) -> str:
    return re.sub(r"([" + re.escape(_ESCAPE_CHARS) + r"])", r"\\\1", text)


def _format_report(title: str, status: str, summary: str, details: list[str], duration: str | None) -> str:
    emoji = _STATUS_EMOJI.get(status, "\u2139\ufe0f")
    lines = [f"{emoji} *{_escape_md2(title)}*", "", _escape_md2(summary)]
    if details:
        lines.append("")
        lines.extend(f"\u2022 {_escape_md2(item)}" for item in details)
    if duration:
        lines.append("")
        lines.append(f"\u23f1 {_escape_md2(duration)}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ntfy",
        description="Send Telegram notifications",
    )
    parser.add_argument("message", nargs="?", help="Message text (use '-' to read from stdin)")
    parser.add_argument("--md", action="store_true", help="Send as MarkdownV2")
    parser.add_argument("--raw", action="store_true", help="Send full stdin as plain text (no tail/code block)")
    parser.add_argument("-n", "--lines", type=int, default=5, help="Number of tail lines in pipe mode (default: 5)")
    parser.add_argument("--header", default=None, help="Header text above the code block (e.g. command name)")
    parser.add_argument("--report", action="store_true", help="Send a structured report")
    parser.add_argument("--report-json", action="store_true", help="Read report JSON from stdin")
    parser.add_argument("--title", default="Report")
    parser.add_argument("--status", default="info", choices=["success", "failure", "info"])
    parser.add_argument("--summary", default="")
    parser.add_argument("--detail", action="append", default=[], dest="details")
    parser.add_argument("--duration", default=None)

    args = parser.parse_args()

    token = _require_env("BOT_TOKEN")
    chat_id = _require_env("CHAT_ID")

    if args.report_json:
        raw = sys.stdin.read()
        data = json.loads(raw)
        text = _format_report(
            title=data.get("title", "Report"),
            status=data.get("status", "info"),
            summary=data.get("summary", ""),
            details=data.get("details", []),
            duration=data.get("duration"),
        )
        _send_message(token, chat_id, text, parse_mode="MarkdownV2")
    elif args.report:
        text = _format_report(
            title=args.title,
            status=args.status,
            summary=args.summary,
            details=args.details,
            duration=args.duration,
        )
        _send_message(token, chat_id, text, parse_mode="MarkdownV2")
    else:
        is_pipe = not sys.stdin.isatty()
        message = args.message

        if message == "-" or (message is None and is_pipe):
            message = sys.stdin.read().strip()

        if not message:
            parser.error("No message provided")

        # Explicit --md or --raw: use old behavior
        if args.md:
            _send_message(token, chat_id, message, parse_mode="MarkdownV2")
        elif args.raw or not is_pipe:
            _send_message(token, chat_id, message)
        else:
            # Smart pipe mode: tail N lines + code block
            all_lines = message.splitlines()
            tail = all_lines[-args.lines:] if len(all_lines) > args.lines else all_lines
            code_body = "\n".join(tail)

            parts: list[str] = []
            if args.header:
                parts.append(f"\U0001f4cb {_escape_md2(args.header)}")
                parts.append("")
            parts.append(f"```\n{code_body}\n```")

            text = "\n".join(parts)
            _send_message(token, chat_id, text, parse_mode="MarkdownV2")

    print("Sent!")


if __name__ == "__main__":
    main()
