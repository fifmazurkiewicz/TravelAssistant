"""
Exception classes for Knowledge Base Service
"""


class KnowledgeBaseException(Exception):
    """Base exception for Knowledge Base Service"""
    pass


class NotFoundError(KnowledgeBaseException):
    """Resource not found"""
    pass


class ValidationError(KnowledgeBaseException):
    """Validation error"""
    pass


class AuthenticationError(KnowledgeBaseException):
    """Authentication error"""
    pass


class AuthorizationError(KnowledgeBaseException):
    """Authorization error"""
    pass


class ExternalServiceError(KnowledgeBaseException):
    """External service error"""
    pass

