from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Query
from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.search.loader import load_documents, load_document
from app.services.indexing_service import IndexingService
from app.search.indexer import InvertedIndex
from app.search.search import SearchEngine

import re

import time
import threading
import os
import psutil


from app.taskflow.tasks import register_task
from pydantic import BaseModel, Field
from datetime import datetime

from app.taskflow.task_manager import TaskManager
from app.taskflow.queue import TaskQueue
from app.taskflow.tasks import Task, TASK_REGISTRY
from app.taskflow.worker import Worker



app = FastAPI(
    title="Document Processing Platform",
    version="0.1.0"
)
print("STATIC PATH:", Path("static").resolve())


app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

#from taskflow
task_manager = TaskManager()
task_queue = TaskQueue()
###########

templates = Jinja2Templates(directory="templates")

DOCUMENTS_DIR = Path("documents")
DOCUMENTS_DIR.mkdir(exist_ok=True)


INDEX_PATH = Path("index/search_index.pkl")

search_index = InvertedIndex()
search_index.load(INDEX_PATH)

search_engine = SearchEngine(search_index)

index_lock = threading.Lock()

indexing_service = IndexingService(
    search_index=search_index,
    index_path=INDEX_PATH,
    index_lock=index_lock
)



register_task(
    "index_document",
    indexing_service.index_document
)

print("[Startup] Search index loaded.")

#from taskflow

workers = []

def calculate_worker_count():
    cpu_cores = os.cpu_count() or 1

    memory = psutil.virtual_memory()
    total_memory_gb = memory.total / (1024 ** 3)

    memory_based_workers = max(1, int(total_memory_gb / 2))
    cpu_based_workers = max(1, cpu_cores - 2)

    return min(
        cpu_based_workers,
        memory_based_workers,
        12
    )


worker_count = calculate_worker_count()

print(
    f"[Platform] Starting {worker_count} workers "
    f"(CPU cores: {os.cpu_count()}, "
    f"RAM: {psutil.virtual_memory().total / (1024 ** 3):.1f} GB)"
)

for i in range(worker_count):
    worker = Worker(
        worker_id=i + 1,
        task_queue=task_queue
    )

    worker.start()
    workers.append(worker)
#####

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )



@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    file_path = DOCUMENTS_DIR / file.filename

    content = await file.read()

    with open(file_path, "wb") as output:
        output.write(content)

    task = Task(
        task_type="index_document",
        args=[str(file_path.resolve())],
        priority=10
    )

    task_manager.add_task(task)
    task_queue.add_task(task)

    return {
        "filename": file.filename,
        "path": str(file_path),
        "task_id": task.id,
        "status": task.status
    }




@app.post("/internal/index")
def internal_index(document_path: str):
    file_path = Path(document_path)

    if not file_path.exists():
        return {
            "document": document_path,
            "status": "failed",
            "error": "Document not found"
        }



    start = time.perf_counter()
    documents = load_document(file_path)
    extraction_time = time.perf_counter() - start

    start = time.perf_counter()

    with index_lock:
        start = time.perf_counter()
        search_index.remove_documents_by_filename(file_path.name)
        remove_time = time.perf_counter() - start

        start = time.perf_counter()
        search_index.add_documents(documents)
        indexing_time = time.perf_counter() - start

        start = time.perf_counter()
        search_index.save(INDEX_PATH)
        save_time = time.perf_counter() - start

    total_time = (
        extraction_time
        + remove_time
        + indexing_time
        + save_time
    )

    print(
        f"[Indexing] {file_path.name} | "
        f"extract={extraction_time:.2f}s | "
        f"remove={remove_time:.2f}s | "
        f"index={indexing_time:.2f}s | "
        f"save={save_time:.2f}s | "
        f"total={total_time:.2f}s"
    )

    return {
        "document": document_path,
        "status": "indexed",
        "documents_added": len(documents),
        "timings": {
            "extraction": round(extraction_time, 2),
            "remove": round(remove_time, 2),
            "indexing": round(indexing_time, 2),
            "save": round(save_time, 2),
            "total": round(total_time, 2)
        }
    }

@app.get("/search")
def search(q: str, algorithm: str = "bm25"):
    if algorithm not in {"bm25", "tfidf"}:
        raise HTTPException(
            status_code=400,
            detail="Algorithm must be 'bm25' or 'tfidf'"
        )

    results = search_engine.search(q, algorithm=algorithm)

    formatted_results = []

    for doc_id, score in results:
        document = search_index.documents.get(doc_id)

        if not document:
            continue

        formatted_results.append({
            "document": doc_id,
            "score": score,
            "snippet": highlight_text(
                create_snippet(document["text"], q),
                q
            ),
            "page": document["page"]
        })

    return {
        "query": q,
        "algorithm": algorithm,
        "results": formatted_results,
        "total_results": len(formatted_results),
        "limit": len(formatted_results)
    }

def create_snippet(text: str, query: str, window: int = 80):
    lower_text = text.lower()
    lower_query = query.lower()

    position = lower_text.find(lower_query)

    if position == -1:
        return text[:window * 2]

    start = max(0, position - window)
    end = min(len(text), position + len(query) + window)

    snippet = text[start:end]

    if start > 0:
        snippet = "..." + snippet

    if end < len(text):
        snippet += "..."

    return snippet

def highlight_text(text: str, query: str):
    if not query.strip():
        return text

    pattern = re.compile(re.escape(query), re.IGNORECASE)

    return pattern.sub(
        lambda match: f"<mark>{match.group(0)}</mark>",
        text
    )

@app.get("/documents")
def get_documents():
    files = []

    for file_path in DOCUMENTS_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in {".pdf", ".txt"}:
            files.append({
                "filename": file_path.name
            })

    files.sort(key=lambda file: file["filename"].lower())

    return {
        "files": files
    }

@app.delete("/documents/{file_name:path}")
def delete_file(file_name: str):
    file_path = DOCUMENTS_DIR / file_name

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="File not found."
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=400,
            detail="Invalid file."
        )

    file_path.unlink()

    search_index.remove_documents_by_filename(
        file_name
    )

    search_index.save(INDEX_PATH)

    return {
        "message": "File deleted and index updated successfully.",
        "filename": file_name
    }

@app.post("/documents/upload-multiple")
async def upload_multiple_documents(
    files: list[UploadFile] = File(...)
):

    start_time = time.perf_counter()


    uploaded = []

    for file in files:
        file_path = DOCUMENTS_DIR / file.filename

        content = await file.read()

        with open(file_path, "wb") as output:
            output.write(content)

        uploaded.append(str(file_path.resolve()))

    #tasks = indexing_service.submit_bulk_indexing_tasks(uploaded)

    tasks = []

    for document_path in uploaded:
        task = Task(
            task_type="index_document",
            args=[document_path],
            priority=10
        )

        task_manager.add_task(task)
        task_queue.add_task(task)

        tasks.append({
            "document": document_path,
            "task_id": task.id,
            "status": task.status
        })


    upload_time = time.perf_counter() - start_time

    print(
        f"[Bulk Upload] "
        f"{len(uploaded)} files submitted | "
        f"time={upload_time:.2f}s"
    )

    return {
        "uploaded": len(uploaded),
        "tasks": tasks,
        "submission_time": round(upload_time, 2)
    }

@app.get("/system-info")
def system_info():
    cpu_cores = os.cpu_count() or 1

    memory = psutil.virtual_memory()
    total_memory_gb = memory.total / (1024 ** 3)

    memory_based_workers = max(
        1,
        int(total_memory_gb / 2)
    )

    cpu_based_workers = max(
        1,
        cpu_cores - 2
    )

    worker_count = min(
        cpu_based_workers,
        memory_based_workers,
        12
    )

    return {
        "system": "Windows",
        "cpu": f"{cpu_cores} cores",
        "ram": f"{total_memory_gb:.1f} GB",
        "workers": worker_count
    }


#taskflow migrants

class TaskRequest(BaseModel):
    task_type: str = Field(min_length=1)
    args: list = Field(default_factory=list)
    kwargs: dict = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0)


class TaskResponse(BaseModel):
    task_id: str
    status: str


class TaskDetailResponse(BaseModel):
    task_id: str
    task_type: str
    status: str
    result: object | None = None
    error: str | None = None


class TaskListItem(BaseModel):
    task_id: str
    task_type: str
    status: str
    result: object | None = None
    error: str | None = None
    priority: int
    created_at: datetime


class CancelResponse(BaseModel):
    task_id: str
    status: str


@app.post("/tasks", response_model=TaskResponse)
def create_task(request: TaskRequest):

    if request.task_type not in TASK_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task type: {request.task_type}"
        )

    task = Task(
        task_type=request.task_type,
        args=request.args,
        kwargs=request.kwargs,
        priority=request.priority
    )

    task_manager.add_task(task)
    task_queue.add_task(task)

    return {
        "task_id": task.id,
        "status": task.status
    }


@app.get("/tasks", response_model=list[TaskListItem])
def list_tasks(
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):

    tasks = task_manager.list_tasks(
        status=status,
        limit=limit,
        offset=offset
    )

    return [
        {
            "task_id": row[0],
            "task_type": row[1],
            "status": row[2],
            "result": row[3],
            "error": row[4],
            "priority": row[5],
            "created_at": row[6]
        }
        for row in tasks
    ]


@app.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def get_task(task_id: str):

    task = task_manager.get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return {
        "task_id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "result": task.result,
        "error": task.error
    }


@app.post(
    "/tasks/{task_id}/cancel",
    response_model=CancelResponse
)
def cancel_task(task_id: str):

    result = task_manager.cancel_task(task_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    if result is False:
        raise HTTPException(
            status_code=400,
            detail="Task cannot be cancelled"
        )

    return {
        "task_id": task_id,
        "status": "cancelled"
    }