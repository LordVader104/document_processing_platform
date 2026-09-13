from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid
import time


@dataclass
class Task:
    task_type: str
    args: list[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    result: Any = None
    error: str | None = None

    max_retries: int = 3
    retry_count: int = 0
    retry_delay: float = 1.0
    cancelled: bool = False
    priority: int = 0

    created_at: datetime = field(default_factory=datetime.now)

def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def sleep_task(seconds):
    time.sleep(seconds)
    return f"Slept for {seconds} seconds"

def fail_task():
    raise RuntimeError("Task failed intentionally")


TASK_REGISTRY = {
    "add": add,
    "multiply": multiply,
    "sleep": sleep_task,
    "fail": fail_task,
}


def register_task(name, function):
    TASK_REGISTRY[name] = function

