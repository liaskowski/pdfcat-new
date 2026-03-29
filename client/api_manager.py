from .api.base import APIBase, APIError
from .api.auth import AuthAPI
from .api.documents import DocumentsAPI
from .api.admin import AdminAPI
from .api.ocr import OCRAPI
from .api.schemas import (
    APICategory, APIFileType, APIFolder, APIFileHistory, APIUser, APIDocument
)

class APIManager(AuthAPI, DocumentsAPI, AdminAPI, OCRAPI):
    """
    Facade class combining all API modules.
    Inherits from specific API classes to provide a single entry point.
    """
    pass
