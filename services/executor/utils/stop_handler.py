

class StopHandler:
    def __init__(self, watched_collection, job_id):
        self.job_id = job_id
        self.watched_collection = watched_collection

    def stop(self):
        c = self.watched_collection.count_documents({"job_id": self.job_id})
        return c == 0
