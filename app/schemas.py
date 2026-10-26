from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    due_date: datetime | None = None
    priority: int = Field(default=3, ge=1, le=5)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    due_date: datetime | None = None
    priority: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            for field in ("title", "status", "priority"):
                if field in values and values[field] is None:
                    raise ValueError(f"{field} cannot be null")
        return values


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    due_date: datetime | None
    priority: int
    created_at: datetime
    updated_at: datetime


class TaskPage(BaseModel):
    items: list[TaskResponse]
    page: int
    limit: int
    total: int


class TaskStats(BaseModel):
    by_status: dict[TaskStatus, int]
    overdue: int
