"""Domain errors raised while extracting uploaded and remote sources."""


class IngestError(Exception):
    """An expected ingestion failure with a user-facing message and HTTP status."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
