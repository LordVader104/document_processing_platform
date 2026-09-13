from queue import PriorityQueue


class TaskQueue:
    def __init__(self):
        self.queue = PriorityQueue()

    def add_task(self, task):
        self.queue.put((-task.priority, task.id, task))

    def get_task(self):
        _, _, task = self.queue.get()
        return task

    def task_done(self):
        self.queue.task_done()

    def join(self):
        self.queue.join()