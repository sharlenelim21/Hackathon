"""Errors raised to the UI. The UI shows `str(error)`, which is the human-readable message."""


class ServiceError(Exception):
    """Error with a machine-readable ``code`` and a human-readable ``message``.

    Codes: validation, bad_file, scanned_pdf, duplicate_file, not_found, wrong_state,
    llm_unavailable.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
