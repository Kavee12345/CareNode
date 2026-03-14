from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    pass


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(status_code=404, detail=f"{resource} not found")


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(status_code=403, detail=detail)


class ConflictError(AppError):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=409, detail=detail)


class ValidationError(AppError):
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(status_code=422, detail=detail)


class StorageError(AppError):
    def __init__(self, detail: str = "Storage operation failed"):
        super().__init__(status_code=500, detail=detail)


class ProcessingError(AppError):
    def __init__(self, detail: str = "Document processing failed"):
        super().__init__(status_code=500, detail=detail)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
