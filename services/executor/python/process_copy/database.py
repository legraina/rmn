import os
import shutil
from datetime import datetime
import cv2
from utils.utils import Document_Status, Job_Status
from utils.storage import Storage, ROOT_DIR
from utils.clients import mongo_client


class Database:
    def __init__(self, db_name="RMN", storage_path=None):
        self.mongo_client = mongo_client()
        self.mongo_database = self.mongo_client[db_name]
        self.storage = Storage(storage_path)

    def close(self):
        self.mongo_client.close()

    def get_collection(self, name):
        return self.mongo_database[name]

    def documents_collection(self):
        return self.get_collection("job_documents")

    def eval_jobs_collection(self):
        return self.get_collection("eval_jobs")

    def jobs_output_collection(self):
        return self.get_collection("jobs_output")

    def users_collection(self):
        return self.get_collection("users")

    def insert_document(
        self,
        job_id,
        doc_index,
        subquestion_pred,
        total,
        image_id,
        status,
        matricule,
        time,
        filename,
    ):
        return self.documents_collection().insert_one(
            {
                "job_id": job_id,
                "document_index": doc_index,
                "matricule": str(matricule),
                "subquestion_predictions": subquestion_pred,
                "total": total,
                "image_id": image_id,
                "status": status.value,
                "execution_time": time,
                "filename": filename,
            }
        )

    def get_document(self, job_id, doc_index):
        return self.documents_collection().find_one({
            "job_id": job_id, "document_index": doc_index
        })

    def update_document(
        self,
        job_id,
        doc_index,
        subquestion_pred,
        total,
        image_id,
        status,
        matricule,
        time,
        max_nb_question,
        group
    ):
        # update alive time stamp
        self.eval_jobs_collection().update_one(
            {"job_id": job_id},
            {"$set": {
                "alive_time": datetime.utcnow(),
                "max_questions": max_nb_question
            }}
        )
        # return updated doc
        return self.documents_collection().update_one(
            {"job_id": job_id, "document_index": doc_index},
            {
                "$set": {
                    "matricule": str(matricule),
                    "subquestion_predictions": subquestion_pred,
                    "total": total,
                    "image_id": image_id,
                    "status": status.value,
                    "execution_time": time,
                    "group": group
                }
            },
        ).matched_count > 0

    def get_job_max_questions(self, job_id):
        doc = self.eval_jobs_collection().find_one({"job_id": job_id})
        if doc:
            return doc["max_questions"]
        return 1

    def update_job_status_to_run(self, job_id, students_list):
        # try to change job status if first try
        self.eval_jobs_collection().update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "job_status": Job_Status.RUN.value,
                    "alive_time": datetime.utcnow(),
                    "students_list": students_list
                }
            }
        )
        return self.eval_jobs_collection().find_one({"job_id": job_id})

    def save_preview_image(self, src, job_id, document_index):
        filename = f"documents/{job_id}/{document_index}.png"
        self.storage.move_to(str(src), filename)
        return filename

    def save_unverified_number_images(self, job_id, document_index, images):
        for index, img in enumerate(images):
            filename = "unverified_number.png"
            self.imwrite_png(filename, img)
            n_png = f"unverified_numbers/{job_id}/{document_index}/{index}.png"
            self.storage.move_to(str(f"numbers/{filename}"), n_png)

        shutil.rmtree(os.path.join("numbers"))

    def get_template_info(self, template_id):
        template = self.mongo_database["template"].find_one(
            {"template_id": template_id}
        )
        template_matricule_box = (
            template["matricule_box"] if "matricule_box" in template else None
        )
        return template["grade_box"], template_matricule_box

    def imwrite_png(self, name, img):
        if not os.path.exists("numbers"):
            os.mkdir("numbers")
        cv2.imwrite(f"numbers/{name}", img)
