from opentime.domain.exceptions import (
    DomainError,
)

DOMAIN_ERROR_STATUS = {
    "not_found": 404,
    "authentication_error": 401,
    "conflict": 409,
    "domain_error": 400,
}


def domain_error_to_http(error: DomainError) -> tuple[int, dict]:
    status_code = DOMAIN_ERROR_STATUS.get(error.code, 400)
    return status_code, {"detail": error.message, "code": error.code}
