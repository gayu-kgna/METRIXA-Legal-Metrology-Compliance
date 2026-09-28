from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, Any, List

T = TypeVar("T")

class ResponseEnvelope(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    error: Optional[dict] = None

class PaginationMeta(BaseModel):
    page: int = 1
    page_size: int = 20
    total_items: int = 0
    total_pages: int = 1
    has_next: bool = False
    has_previous: bool = False
    total: Optional[int] = None
    pages: Optional[int] = None

    def model_post_init(self, __context: Any) -> None:
        if self.total is None:
            self.total = self.total_items
        if self.pages is None:
            self.pages = self.total_pages

class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: List[T] = []
    pagination: Optional[PaginationMeta] = None
    items: Optional[List[T]] = None
    meta: Optional[PaginationMeta] = None

    def model_post_init(self, __context: Any) -> None:
        if self.items is None:
            self.items = self.data
        if self.meta is None:
            self.meta = self.pagination
