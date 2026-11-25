import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError

logger = logging.getLogger("oralsense")


class AppError(Exception):
    """An expected failure with a stable machine-readable code and a user-safe message."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields


def database_not_configured() -> AppError:
    return AppError(
        503,
        "database_not_configured",
        "The database is not configured.",
    )


def database_unavailable() -> AppError:
    return AppError(
        503,
        "database_unavailable",
        "The database is unavailable.",
    )


def error_body(code: str, message: str, fields: dict[str, str] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "fields": fields}}


def _field_name(loc: tuple) -> str:
    # Drop the "body"/"query" prefix so the frontend can map errors straight onto inputs.
    parts = [str(part) for part in loc if part not in ("body", "query", "path")]
    return ".".join(parts) or "request"


def _readable_validation_message(error: dict) -> str:
    error_type = error.get("type")
    context = error.get("ctx") or {}
    if error_type == "string_too_short":
        return f"Must be at least {context.get('min_length')} characters."
    if error_type == "string_too_long":
        return f"Must be at most {context.get('max_length')} characters."
    if error_type == "missing":
        return "This field is required."
    if error_type == "value_error" and "email" in str(error.get("msg", "")).lower():
        return "Enter a valid email address."
    message = error.get("msg", "Invalid value.")
    # Pydantic prefixes custom ValueError messages; strip it for users.
    return message.removeprefix("Value error, ")


async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, exc.fields),
    )


async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields: dict[str, str] = {}
    for error in exc.errors():
        name = _field_name(tuple(error.get("loc", ())))
        fields.setdefault(name, _readable_validation_message(error))
    return JSONResponse(
        status_code=422,
        content=error_body("validation_error", "Some fields need attention.", fields),
    )


async def handle_database_connection_error(_: Request, exc: Exception) -> JSONResponse:
    logger.error("Database connection failed: %s", type(exc).__name__)
    error = database_unavailable()
    return JSONResponse(status_code=error.status_code, content=error_body(error.code, error.message))


async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    # Type only: exception text must not reach logs (may contain provider or key material).
    logger.error("Unhandled server error (%s)", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content=error_body("internal_error", "Something went wrong on the server. Please try again."),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(OperationalError, handle_database_connection_error)
    app.add_exception_handler(InterfaceError, handle_database_connection_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
