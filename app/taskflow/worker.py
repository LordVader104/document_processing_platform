import time
from threading import Thread

import psycopg

from app.taskflow.queue import TaskQueue
from app.taskflow.tasks import TASK_REGISTRY
from app.taskflow.config import DATABASE_URL

def execute_task(task, conn):
    task.status = "running"

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE tasks
            SET status = 'running'
            WHERE id = %s
            """,
            (task.id,)
        )

    conn.commit()

    try:
        function = TASK_REGISTRY[task.task_type]

        task.result = function(
            *task.args,
            **task.kwargs
        )

        task.status = "completed"

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET status = 'completed',
                    result = %s,
                    error = NULL,
                    retry_count = %s
                WHERE id = %s
                """,
                (
                    psycopg.types.json.Jsonb(task.result),
                    task.retry_count,
                    task.id
                )
            )

        conn.commit()

        return True

    except Exception as error:
        task.retry_count += 1
        task.error = str(error)

        print(
            f"[Worker] Task {task.id} failed: "
            f"{type(error).__name__}: {error}"
        )

        if task.retry_count <= task.max_retries:
            task.status = "retrying"

            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE tasks
                    SET status = 'retrying',
                        error = %s,
                        retry_count = %s
                    WHERE id = %s
                    """,
                    (
                        task.error,
                        task.retry_count,
                        task.id
                    )
                )

            conn.commit()

            print(
                f"[Worker] Task {task.id} failed. "
                f"Retry {task.retry_count}/{task.max_retries}"
            )

            return False

        task.status = "failed"

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET status = 'failed',
                    error = %s,
                    retry_count = %s
                WHERE id = %s
                """,
                (
                    task.error,
                    task.retry_count,
                    task.id
                )
            )

        conn.commit()

        return True


class Worker:
    def __init__(self, worker_id, task_queue):
        self.worker_id = worker_id
        self.task_queue = task_queue

        self.thread = Thread(
            target=self.run,
            daemon=True
        )

    def start(self):
        self.thread.start()

    def is_cancelled(self, task_id):
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT status
                    FROM tasks
                    WHERE id = %s
                    """,
                    (task_id,)
                )

                row = cur.fetchone()

        return row is not None and row[0] == "cancelled"

    def run(self):
        with psycopg.connect(DATABASE_URL) as conn:
            while True:
                task = self.task_queue.get_task()

                if self.is_cancelled(task.id):
                    print(
                        f"[Worker {self.worker_id}] "
                        f"Task {task.id} was cancelled"
                    )

                    self.task_queue.task_done()
                    continue

                print(
                    f"[Worker {self.worker_id}] "
                    f"Processing task: {task.id} "
                    f"(priority={task.priority})"
                )

                completed = execute_task(task, conn)

                if not completed:
                    delay = task.retry_delay * (
                        2 ** (task.retry_count - 1)
                    )

                    print(
                        f"[Worker {self.worker_id}] "
                        f"Retrying task {task.id} "
                        f"in {delay:.1f} seconds"
                    )

                    self.task_queue.task_done()

                    time.sleep(delay)

                    self.task_queue.add_task(task)

                else:
                    print(
                        f"[Worker {self.worker_id}] "
                        f"Task {task.id} "
                        f"finished with status: {task.status}"
                    )

                    self.task_queue.task_done()