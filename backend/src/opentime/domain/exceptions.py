class DomainError(Exception):
    """Base class for domain-level errors."""

    def __init__(self, message: str, code: str = "domain_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(DomainError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="not_found")


class AuthenticationError(DomainError):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="authentication_error")


class ConflictError(DomainError):
    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(message, code="conflict")
