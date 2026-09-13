import json
import psycopg

from app.taskflow.tasks import Task
from app.taskflow.config import DATABASE_URL


class TaskManager:
    def add_task(self, task: Task):
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tasks (
                        id,
                        task_type,
                        args,
                        kwargs,
                        status,
                        result,
                        error,
                        max_retries,
                        retry_count,
                        retry_delay,
                        priority,
                        created_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        task.id,
                        task.task_type,
                        json.dumps(task.args),
                        json.dumps(task.kwargs),
                        task.status,
                        None,
                        task.error,
                        task.max_retries,
                        task.retry_count,
                        task.retry_delay,
                        task.priority,
                        task.created_at
                    )
                )

    def get_task(self, task_id: str):
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        task_type,
                        args,
                        kwargs,
                        status,
                        result,
                        error,
                        max_retries,
                        retry_count,
                        retry_delay,
                        priority,
                        created_at
                    FROM tasks
                    WHERE id = %s
                    """,
                    (task_id,)
                )

                row = cur.fetchone()

        if row is None:
            return None

        task = Task(
            task_type=row[1],
            args=row[2],
            kwargs=row[3],
            id=row[0]
        )

        task.status = row[4]
        task.result = row[5]
        task.error = row[6]
        task.max_retries = row[7]
        task.retry_count = row[8]
        task.retry_delay = row[9]
        task.priority = row[10]
        task.created_at = row[11]

        return task

    def list_tasks(self, status=None, limit=20, offset=0):
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                if status is None:
                    cur.execute(
                        """
                        SELECT
                            id,
                            task_type,
                            status,
                            result,
                            error,
                            priority,
                            created_at
                        FROM tasks
                        ORDER BY created_at DESC
                        LIMIT %s
                        OFFSET %s
                        """,
                        (limit, offset)
                    )
                else:
                    cur.execute(
                        """
                        SELECT
                            id,
                            task_type,
                            status,
                            result,
                            error,
                            priority,
                            created_at
                        FROM tasks
                        WHERE status = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        OFFSET %s
                        """,
                        (status, limit, offset)
                    )

                rows = cur.fetchall()

        return rows

    def cancel_task(self, task_id: str):
        task = self.get_task(task_id)

        if task is None:
            return None

        if task.status in ("completed", "failed", "cancelled"):
            return False

        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE tasks
                    SET status = 'cancelled'
                    WHERE id = %s
                    """,
                    (task_id,)
                )

        return True