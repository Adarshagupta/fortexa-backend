from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

# News schemas
class NewsResponse(BaseModel):
    id: str
    title: str
    content: str
    summary: Optional[str] = None
    author: Optional[str] = None
    source: str
    source_url: str
    image_url: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    published_at: datetime
    sentiment: Optional[float] = None  # -1 to 1
    relevance_score: Optional[float] = None  # 0 to 1
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class NewsListResponse(BaseModel):
    news: List[NewsResponse]
    total_count: int
    category: Optional[str] = None

class CreateNewsRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    summary: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=100)
    source: str = Field(..., min_length=1, max_length=100)
    source_url: str = Field(..., min_length=1)
    image_url: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    tags: List[str] = []
    published_at: datetime
    sentiment: Optional[float] = Field(None, ge=-1, le=1)
    relevance_score: Optional[float] = Field(None, ge=0, le=1)

class UpdateNewsRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    summary: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=100)
    source: Optional[str] = Field(None, min_length=1, max_length=100)
    source_url: Optional[str] = Field(None, min_length=1)
    image_url: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    sentiment: Optional[float] = Field(None, ge=-1, le=1)
    relevance_score: Optional[float] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None 
from pydantic import BaseModel, Field
from datetime import datetime

# News schemas
class NewsResponse(BaseModel):
    id: str
    title: str
    content: str
    summary: Optional[str] = None
    author: Optional[str] = None
    source: str
    source_url: str
    image_url: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    published_at: datetime
    sentiment: Optional[float] = None  # -1 to 1
    relevance_score: Optional[float] = None  # 0 to 1
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class NewsListResponse(BaseModel):
    news: List[NewsResponse]
    total_count: int
    category: Optional[str] = None

class CreateNewsRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    summary: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=100)
    source: str = Field(..., min_length=1, max_length=100)
    source_url: str = Field(..., min_length=1)
    image_url: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    tags: List[str] = []
    published_at: datetime
    sentiment: Optional[float] = Field(None, ge=-1, le=1)
    relevance_score: Optional[float] = Field(None, ge=0, le=1)

class UpdateNewsRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    summary: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=100)
    source: Optional[str] = Field(None, min_length=1, max_length=100)
    source_url: Optional[str] = Field(None, min_length=1)
    image_url: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    sentiment: Optional[float] = Field(None, ge=-1, le=1)
    relevance_score: Optional[float] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None 
 