"""
Pydantic models/schemas for request/response validation.
"""

from typing import Optional, List
from pydantic import BaseModel, field_validator

from app.config import VALID_STATUSES, VALID_PRIORITIES, MAX_ATTACHMENT_SIZE_BYTES, MAX_ATTACHMENT_SIZE_MB


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    status: str = "Backlog"
    priority: str = "Medium"
    agent: str = "Unassigned"
    due_date: Optional[str] = None
    board: str = "tasks"
    source_file: Optional[str] = None
    source_ref: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v not in VALID_STATUSES:
            raise ValueError(f'Invalid status "{v}". Must be one of: {VALID_STATUSES}')
        return v

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v not in VALID_PRIORITIES:
            raise ValueError(f'Invalid priority "{v}". Must be one of: {VALID_PRIORITIES}')
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    agent: Optional[str] = None
    due_date: Optional[str] = None
    source_file: Optional[str] = None
    source_ref: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f'Invalid status "{v}". Must be one of: {VALID_STATUSES}')
        return v

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v is not None and v not in VALID_PRIORITIES:
            raise ValueError(f'Invalid priority "{v}". Must be one of: {VALID_PRIORITIES}')
        return v


class Task(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    agent: str
    due_date: Optional[str]
    created_at: str
    updated_at: str
    board: str
    source_file: Optional[str] = None
    source_ref: Optional[str] = None
    working_agent: Optional[str] = None


class MoveRequest(BaseModel):
    status: str
    agent: str = None
    reason: str = None


class CommentCreate(BaseModel):
    agent: str
    content: str

    @field_validator('content')
    @classmethod
    def validate_content_size(cls, v):
        if len(v) > MAX_ATTACHMENT_SIZE_BYTES:
            raise ValueError(f'Content exceeds maximum size of {MAX_ATTACHMENT_SIZE_MB}MB')
        return v

    @field_validator('agent')
    @classmethod
    def validate_agent(cls, v):
        if len(v) > 100:
            raise ValueError('Agent name too long')
        return v


class ActionItemCreate(BaseModel):
    agent: str
    content: str
    item_type: str = "question"
    comment_id: Optional[int] = None


class ImageUpload(BaseModel):
    data: str
    filename: Optional[str] = "image"


class JarvisMessage(BaseModel):
    message: str
    session: str = "main"
    attachments: Optional[List[dict]] = None

    @field_validator('message')
    @classmethod
    def validate_message_size(cls, v):
        if len(v) > MAX_ATTACHMENT_SIZE_BYTES:
            raise ValueError(f'Message exceeds maximum size of {MAX_ATTACHMENT_SIZE_MB}MB')
        return v


class JarvisResponse(BaseModel):
    response: str
    session: str = "main"

    @field_validator('response')
    @classmethod
    def validate_response_size(cls, v):
        if len(v) > 1024 * 1024:
            raise ValueError('Response too large')
        return v


class SessionCreate(BaseModel):
    label: str = None
    agentId: str = "main"
    task: str = "New session started from Task Board. Awaiting instructions."
