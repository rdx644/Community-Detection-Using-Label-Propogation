"""Actionable domain failures, without raw data or internal traceback content."""

from typing import Any


class AnalysisError(Exception):
    def __init__(
        self, code: str, message: str, status: int = 422, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}

    def payload(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}
