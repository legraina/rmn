import uuid
import configparser
import os
import shutil
import cv2

from pymongo import MongoClient
from pathlib import Path
from utils.utils import Document_Status, Job_Status
import pyrebase

CONFIG_FILE = (
    Path(__file__)
    .resolve()
    .parent.parent.parent.joinpath("config")
    .joinpath("config.ini")
)

parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
parser.read(CONFIG_FILE)

URL = parser.get("MONGODB", "URL")

firebaseConfig = {
    "apiKey": "AIzaSyAPHNsT4BQjbvC_NNgu0BB3YXPZy1vioNU",
    "authDomain": "projet4-bcfe5.firebaseapp.com",
    "projectId": "projet4-bcfe5",
    "storageBucket": "projet4-bcfe5.appspot.com",
    "messagingSenderId": "171342986362",
    "appId": "1:171342986362:web:018b05e620c609a2ce0fc3",
    "measurementId": "G-E9P71RH1DF",
    "databaseURL": "",
}


class Database:
    def __init__(self, db_name):
        self.mongo_client = MongoClient(URL)
        self.mongo_database = self.mongo_client[db_name]
        self.firebase_storage = pyrebase.initialize_app(firebaseConfig).storage()

    def insert_document(
        self,
        collection_name,
        job_id,
        doc_index,
        subquestion_pred,
        total,
        image_id,
        status,
        matricule,
        students_list,
        time,
        n_total_doc,
        filename,
    ):
        return self.mongo_database[collection_name].insert_one(
            {
                "job_id": job_id,
                "document_index": doc_index,
                "matricule": str(matricule),
                "subquestion_predictions": subquestion_pred,
                "total": total,
                "image_id": image_id,
                "status": status.value,
                "students_list": students_list,
                "execution_time": time,
                "n_total_doc": n_total_doc,
                "filename": filename,
            }
        )

    def update_document(
        self,
        collection_name,
        job_id,
        doc_index,
        subquestion_pred,
        total,
        image_id,
        status,
        matricule,
        time,
        n_total_doc,
    ):
        return self.mongo_database[collection_name].update_one(
            {"job_id": job_id, "document_index": doc_index},
            {
                "$set": {
                    "matricule": str(matricule),
                    "subquestion_predictions": subquestion_pred,
                    "total": total,
                    "image_id": image_id,
                    "status": status.value,
                    "execution_time": time,
                    "n_total_doc": n_total_doc,
                }
            },
        )

    def update_job_status(self, collection_name, job_id, status):
        return self.mongo_database[collection_name].update_one(
            {"job_id": job_id},
            {"$set": {"job_status": status.value}},
        )

    def save_preview_image(self, src, job_id, document_index):
        filename = f"documents/{job_id}_{document_index}.png"
        self.firebase_storage.child(filename).put(str(src))
        os.remove(str(src))
        return filename

    def save_unverified_number_images(self, job_id, document_index, images):
        for index, img in enumerate(images):

            filename = "unverified_number.png"
            self.imwrite_png(filename, img)
            self.firebase_storage.child(
                f"unverified_numbers/{job_id}/{document_index}/{index}.png"
            ).put(str(os.path.join(f"numbers/{filename}")))

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
