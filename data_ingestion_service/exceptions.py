"""
Exception classes for Data Ingestion Service
"""


class DataIngestionException(Exception):
    """Base exception for Data Ingestion Service"""
    pass


class NotFoundError(DataIngestionException):
    """Resource not found"""
    pass


class ValidationError(DataIngestionException):
    """Validation error"""
    pass


class ExternalServiceError(DataIngestionException):
    """External service error"""
    pass

