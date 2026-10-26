from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Task, User
from app.schemas import (
    LoginRequest,
    TaskCreate,
    TaskPage,
    TaskResponse,
    TaskStats,
    TaskStatus,
    TaskUpdate,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.security import create_access_token, hash_password, verify_password

app = FastAPI(title="Task Management API", version="1.0.0")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    email = str(payload.email).lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered") from None
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(func.lower(User.email) == str(payload.email).lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        token = create_access_token(user.id)
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)) from error
    return TokenResponse(access_token=token)


@app.get("/users/me", response_model=UserResponse)
def get_current_user_profile(user: User = Depends(get_current_user)) -> User:
    return user


def _owned_task_or_404(task_id: int, user: User, db: Session) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    task = Task(user_id=user.id, **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=TaskPage)
def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    priority: int | None = Query(default=None, ge=1, le=5),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskPage:
    filters = [Task.user_id == user.id]
    if status_filter is not None:
        filters.append(Task.status == status_filter.value)
    if priority is not None:
        filters.append(Task.priority == priority)
    total = db.scalar(select(func.count()).select_from(Task).where(*filters)) or 0
    due_order = Task.due_date.asc().nullslast() if sort == "asc" else Task.due_date.desc().nullslast()
    items = db.scalars(
        select(Task)
        .where(*filters)
        .order_by(due_order, Task.id.asc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return TaskPage(items=items, page=page, limit=limit, total=total)


@app.get("/tasks/stats", response_model=TaskStats)
def task_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskStats:
    counts = dict(
        db.execute(
            select(Task.status, func.count(Task.id))
            .where(Task.user_id == user.id)
            .group_by(Task.status)
        ).all()
    )
    by_status = {task_status: counts.get(task_status.value, 0) for task_status in TaskStatus}
    now = datetime.now(timezone.utc)
    overdue = db.scalar(
        select(func.count(Task.id)).where(
            Task.user_id == user.id,
            Task.due_date.is_not(None),
            Task.due_date < now,
            Task.status != TaskStatus.DONE.value,
        )
    ) or 0
    return TaskStats(by_status=by_status, overdue=overdue)


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    return _owned_task_or_404(task_id, user, db)


@app.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    task = _owned_task_or_404(task_id, user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    task = _owned_task_or_404(task_id, user, db)
    db.delete(task)
    db.commit()
