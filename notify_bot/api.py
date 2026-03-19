from __future__ import annotations

from typing import Literal

from aiogram.exceptions import TelegramBadRequest
from fastapi import FastAPI
from pydantic import BaseModel, model_validator

from notify_bot.bot import send_notification
from notify_bot.formatting import format_report

app = FastAPI(title="ntfy", version="0.1.0")


class Report(BaseModel):
    title: str
    status: str = "info"  # success | failure | info
    summary: str
    details: list[str] = []
    duration: str | None = None


class NotifyRequest(BaseModel):
    message: str | None = None
    format: Literal["text", "markdown", "report"] = "text"
    report: Report | None = None

    @model_validator(mode="after")
    def check_fields(self) -> NotifyRequest:
        if self.format == "report" and self.report is None:
            raise ValueError("'report' field is required when format is 'report'")
        if self.format in ("text", "markdown") and not self.message:
            raise ValueError("'message' field is required when format is 'text' or 'markdown'")
        return self


class NotifyResponse(BaseModel):
    ok: bool
    error: str | None = None


@app.post("/notify", response_model=NotifyResponse)
async def notify(req: NotifyRequest) -> NotifyResponse:
    try:
        if req.format == "report":
            r = req.report
            text = format_report(
                title=r.title,
                status=r.status,
                summary=r.summary,
                details=r.details,
                duration=r.duration,
            )
            await send_notification(text, parse_mode="MarkdownV2")
        elif req.format == "markdown":
            await send_notification(req.message, parse_mode="MarkdownV2")
        else:
            await send_notification(req.message)
    except TelegramBadRequest as e:
        return NotifyResponse(ok=False, error=str(e))

    return NotifyResponse(ok=True)
