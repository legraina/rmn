from service.template_service import TemplateService
from service.user_service import UserService, Role
from pymongo import MongoClient
from flask import Flask, request, Response, json, send_file, after_this_request
from flask_cors import CORS, cross_origin
from werkzeug.utils import secure_filename
from pathlib import Path
from utils.utils import Job_Status, Output_File, Document_Status
from utils.storage import Storage
from datetime import datetime, timezone
from io import FileIO
from PyPDF2 import PdfWriter, PdfReader
from service.front_page_service import FrontPageHandler
from threading import Thread

import configparser
import uuid
import os
import redis
import json
import pandas as pd
import pytz
import socketio
import shutil
import time
from functools import wraps


ROOT_DIR = Path(__file__).resolve().parent

TEMP_FOLDER = ROOT_DIR.joinpath("temp")

VALIDATE_TEMP_FOLDER = ROOT_DIR.joinpath("validate_temp_folder")

CONFIG_FILE = ROOT_DIR.joinpath("config").joinpath("config.ini")

FRONT_PAGE_TEMP_FOLDER = ROOT_DIR.joinpath("front_page_temp")

LATEX_INPUT_FILE = ROOT_DIR.joinpath("data.tex")

app = Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
parser.read(CONFIG_FILE)
mongo_url = parser.get("MONGODB", "URL")
mongo_client = MongoClient(mongo_url)

redis_host = "redis" if os.getenv("ENVIRONNEMENT") == "production" else "localhost"
socketio_host = (
    "socketio" if os.getenv("ENVIRONNEMENT") == "production" else "localhost"
)

r = redis.Redis(host=redis_host, port=6379, db=0)

storage = Storage()


def verify_token(role=None):
    def _verify_token(f):
        @wraps(f)
        def __verify_token(*args, **kwargs):
            # check if token provided
            if "token" not in request.form:
                return Response(
                    response=json.dumps({"response": f"Error: token not provided."}),
                    status=400,
                )
            # check if token valid
            db = mongo_client["RMN"]
            token = request.form['token']
            if not UserService.verify_token(token, db, role):
                return Response(
                    response=json.dumps({"response": f"Error: token not valid. Please login."}),
                    status=400,
                )
            return f()
        return __verify_token
    return _verify_token


@app.route("/")
def say_hello():
    return "<h1>Hi Andy, I'm on fire !</h1>"


@app.route("/login", methods=["POST"])
@cross_origin()
def login():
    db = mongo_client["RMN"]
    return UserService.login(request, db)


@app.route("/signup", methods=["POST"])
@cross_origin()
@verify_token(Role.ADMIN)
def signup():
    db = mongo_client["RMN"]
    return UserService.signup(request, db)


@app.route("/updateSaveVerifiedImages", methods=["PUT"])
@cross_origin()
@verify_token()
def update_user():
    db = mongo_client["RMN"]
    return UserService.update_save_verified_images(request, db)

@app.route("/updateMoodleStructureInd", methods=["PUT"])
@cross_origin()
@verify_token()
def update_moodle_structure_ind():
    db = mongo_client["RMN"]
    return UserService.update_moodle_structure_ind(request, db)


@app.route("/password", methods=["POST"])
@cross_origin()
@verify_token()
def change_password():
    db = mongo_client["RMN"]
    return UserService.change_password(request, db, True)


@app.route("/evaluate", methods=["POST"])
@cross_origin()
@verify_token()
def evaluate():
    request_form = request.form

    if "user_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: user_id not provided."}),
            status=400,
        )

    if "template_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: template_id not provided."}),
            status=400,
        )

    if "nb_pages" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: nb_pages not provided."}),
            status=400,
        )

    if "job_name" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: job_name not provided."}),
            status=400,
        )

    if "template_name" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: template_name not provided."}),
            status=400,
        )

    print(request.files)

    if not request.files:
        return Response(
            response=json.dumps({"response": f"Error: No files provided."}),
            status=400,
        )

    if "notes_csv_file" not in request.files:
        return Response(
            response=json.dumps({"response": f"Error: Notes csv file not provided."}),
            status=400,
        )

    if "zip_file" not in request.files:
        return Response(
            response=json.dumps({"response": f"Error: Zip file not provided."}),
            status=400,
        )

    user_id = str(request_form["user_id"])

    template_id = str(request_form["template_id"])
    template_name = str(request_form["template_name"])
    job_name = str(request_form["job_name"])
    nb_pages = int(request_form["nb_pages"])

    # Define db and collection used
    db = mongo_client["RMN"]
    collection = db["eval_jobs"]

    job_id = str(uuid.uuid4())

    path_on_cloud_zip = "zips/"
    zip_file_id = f"{path_on_cloud_zip}{job_id}.zip"

    path_on_cloud_csv = "csv/"
    notes_file_id = f"{path_on_cloud_csv}{job_id}.csv"

    job = {
        "job_id": job_id,
        "job_name": job_name,
        "user_id": user_id,
        "template_id": template_id,
        "template_name": template_name,
        "queued_time": datetime.utcnow(),
        "job_status": Job_Status.QUEUED.value,
        "notes_file_id": notes_file_id,
        "zip_file_id": zip_file_id,
        "students_list": []
    }

    try:
        collection.insert_one(job)
    except Exception as e:
        print(e)
        return Response(
            response=json.dumps({"response": f"Error: Failed to insert in MongoDB."}),
            status=500,
        )

    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    try:
        notes_csv_file = request.files.get("notes_csv_file")
        notes_csv_file_name = secure_filename(notes_csv_file.filename)
        notes_csv_file.save(FileIO(TEMP_FOLDER.joinpath(notes_csv_file_name), "wb"))

        zip_file = request.files.get("zip_file")
        zip_file_name = secure_filename(zip_file.filename)

        # transform into zip file
        if str(zip_file_name).endswith(".pdf"):
            reader = PdfReader(zip_file)
            folder_to_zip = TEMP_FOLDER.joinpath("folder_to_zip")

            if not os.path.exists(folder_to_zip):
                os.makedirs(folder_to_zip)

            current_idx = 0
            writer = PdfWriter()
            for p in reader.pages:
                writer.add_page(p)
                if len(writer.pages) == nb_pages:
                    with open(
                        str(folder_to_zip.joinpath(f"{str(current_idx)}.pdf")), "wb"
                    ) as out:
                        writer.write(out)
                    writer = PdfWriter()
                    current_idx += 1
            if len(writer.pages) > 0:
                print("WARNING: there are some pages that will be lost:", len(writer.pages))

            zip_file_name = "copies.zip"
            shutil.make_archive(
                str(TEMP_FOLDER.joinpath("copies")), "zip", str(folder_to_zip)
            )

            shutil.rmtree(str(folder_to_zip))
        else:
            with open(str(TEMP_FOLDER.joinpath(zip_file_name)), "wb") as f_out:
                print("here")
                file_content = zip_file.stream.read()
                f_out.write(file_content)

    except Exception as e:
        print(e)
        return Response(response=f"Error: Failed to download files.", status=900)

    # Create SocketIO connection
    sio = socketio.Client()
    sio.connect(f"http://{socketio_host}:7000")

    sio.emit(
        "jobs_status",
        json.dumps(
            {"job_id": job_id, "status": Job_Status.QUEUED.value, "user_id": user_id}
        ),
    )

    sio.disconnect()

    thread = Thread(target=evaluate_thread,
                    kwargs={
                        "job_id": job_id,
                        "notes_file_id": notes_file_id,
                        "zip_file_id": zip_file_id,
                        "job": job,
                        "user_id": user_id,
                        "zip_file_name": zip_file_name,
                        "notes_csv_file_name": notes_csv_file_name
                    })
    thread.start()

    return Response(response=json.dumps({"response": "OK"}), status=200)

def evaluate_thread(job_id, notes_file_id, zip_file_id, job, user_id, zip_file_name, notes_csv_file_name):
    try:
        file_name = str(TEMP_FOLDER.joinpath(zip_file_name))
        storage.move_to(file_name, zip_file_id)

        file_name = str(TEMP_FOLDER.joinpath(notes_csv_file_name))
        storage.move_to(file_name, notes_file_id)
    except Exception as e:
        print(e, "311")

        # Create SocketIO connection
        sio = socketio.Client()
        sio.connect(f"http://{socketio_host}:7000")

        db = mongo_client["RMN"]
        collection_eval_jobs = db["eval_jobs"]

        collection_eval_jobs.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "job_status": Job_Status.ERROR.value,
                    }
                },
            )

        sio.emit(
            "jobs_status",
            json.dumps(
                {
                    "job_id": job_id,
                    "user_id": user_id,
                    "status": Job_Status.ERROR.value,
                }
            ),
        )
        sio.disconnect()
        exit()

    # add to Redis Queue
    queue_object = {
        "job_type": "execution",
        "job_id": job["job_id"],
        "user_id": job["user_id"]
    }
    r.rpush("job_queue", json.dumps(queue_object))


@app.route("/template", methods=["POST"])
@cross_origin()
@verify_token()
def create_template():
    db = mongo_client["RMN"]
    return TemplateService.create_template(request, db, storage)


@app.route("/user/template", methods=["POST"])
@cross_origin()
@verify_token()
def get_all_template_info():
    db = mongo_client["RMN"]
    return TemplateService.get_all_template_info(request, db)


@app.route("/template/delete", methods=["POST"])
@cross_origin()
@verify_token()
def delete_template():
    db = mongo_client["RMN"]
    return TemplateService.delete_template(request, db, storage)


@app.route("/template/info", methods=["POST"])
@cross_origin()
@verify_token()
def get_template_info():
    db = mongo_client["RMN"]
    return TemplateService.get_template_info(request, db)


@app.route("/template/download", methods=["POST"])
@cross_origin()
@verify_token()
def download_template():
    db = mongo_client["RMN"]
    return TemplateService.download_template_file(request, db, storage)


@app.route("/template/modify", methods=["POST"])
@cross_origin()
@verify_token()
def modify_template():
    db = mongo_client["RMN"]
    return TemplateService.change_template_info(request, db)


@app.route("/jobs", methods=["POST"])
@cross_origin()
@verify_token()
def get_jobs():
    # Define db and collection used
    db = mongo_client["RMN"]
    collection = db["eval_jobs"]

    request_form = request.form
    if "user_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: user_id not provided."}),
            status=400,
        )
    user_id = str(request_form["user_id"])

    # Get all jobs from DB
    jobs = collection.find({"user_id": user_id})

    #
    resp = [
        {
            "job_id": job["job_id"],
            "template_id": job["template_id"],
            "queued_time": str(job["queued_time"]),
            "job_status": job["job_status"],
            "job_name": job["job_name"],
            "template_name": job["template_name"],
        }
        for job in jobs
    ]

    #
    return Response(response=json.dumps({"response": resp}), status=200)


@app.route("/job", methods=["POST"])
@cross_origin()
@verify_token()
def get_job():
    # Define db and collection used
    db = mongo_client["RMN"]
    collection = db["eval_jobs"]

    request_form = request.form
    if "job_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: job_id not provided."}),
            status=400
        )
    job_id = str(request_form["job_id"])

    # Get all jobs from DB
    job = collection.find_one({"job_id": job_id})
    if job is None:
        return Response(
            response=json.dumps({"response": f"Error: job {job_id} doesn't exist."}),
            status=400
        )

    #
    resp = {
        "job_id": job["job_id"],
        "template_id": job["template_id"],
        "queued_time": str(job["queued_time"]),
        "job_status": job["job_status"],
        "job_name": job["job_name"],
        "template_name": job["template_name"],
        "students_list": job["students_list"]
    }
    return Response(response=json.dumps({"response": resp}), status=200)


@app.route("/file/download", methods=["POST"])
@cross_origin()
@verify_token()
def download_file():
    #
    request_form = request.form

    #
    if "job_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: job_id not provided."}),
            status=400,
        )

    #
    if "file" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: file not provided."}),
            status=400,
        )

    #
    job_id = str(request_form["job_id"])

    # TODO: validation pour job_id

    target_file = str(request_form["file"])
    try:
        target_file = Output_File(target_file)
    except Exception as e:
        print(e)
        return Response(
            response=json.dumps(
                {"response": f"Error: invalid value for 'file' param."}
            ),
            status=400,
        )
    if "zip_index" not in request_form and target_file == Output_File.ZIP_FILE:
        return Response(
            response=json.dumps({"response": f"Error: zip_index not provided."}),
            status=400,
        )

    #
    db = mongo_client["RMN"]
    output_collection = db["jobs_output"]

    #
    output_files = output_collection.find_one({"job_id": job_id})

    #
    output_file_mapping_dict = {
        Output_File.NOTES_CSV_FILE: "notes_csv_file_id",
        Output_File.PREVIEW_FILE: "preview_file_id",
        Output_File.ZIP_FILE: "moodle_zip_id_list",
    }

    target_output_file = output_file_mapping_dict[target_file]

    file_id = output_files[target_output_file]

    if target_file == Output_File.ZIP_FILE:
        zip_index = int(request_form["zip_index"])
        print(output_files)
        print(output_files[target_output_file])
        file_id = output_files[target_output_file][zip_index]

    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)

    # Save file to local
    filepath = str(TEMP_FOLDER.joinpath(file_id.split("/")[-1]))
    storage.copy_from(file_id, filepath)
    print("file created")

    file_send = send_file(filepath)

    os.remove(filepath)

    return file_send


@app.route("/job/batch/info", methods=["POST"])
@cross_origin()
@verify_token()
def get_info_zip():
    request_form = request.form

    if "job_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: job_id not provided."}),
            status=400,
        )
    #
    job_id = str(request_form["job_id"])

    #
    db = mongo_client["RMN"]
    output_collection = db["jobs_output"]

    #
    output_files = output_collection.find_one({"job_id": job_id})
    print(output_files)
    #
    resp = len(output_files["moodle_zip_id_list"])

    #
    return Response(response=json.dumps({"response": resp}), status=200)


@app.route("/documents", methods=["POST"])
@cross_origin()
@verify_token()
def get_documents():
    request_form = request.form

    if "job_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: job_id not provided."}),
            status=400,
        )

    #
    job_id = str(request_form["job_id"])

    #
    db = mongo_client["RMN"]
    collection = db["job_documents"]

    #
    docs = collection.find({"job_id": job_id})
    count = collection.count_documents({"job_id": job_id})

    #
    resp = [
        {
            "job_id": doc["job_id"],
            "document_index": doc["document_index"],
            "subquestion_predictions": doc["subquestion_predictions"],
            "matricule": doc["matricule"],
            "total": doc["total"],
            "status": doc["status"],
            "exec_time": doc["execution_time"],
            "n_total_doc": count
        }
        for doc in docs
    ]

    #
    return Response(response=json.dumps({"response": resp}), status=200)


@app.route("/documents/update", methods=["POST"])
@cross_origin()
@verify_token()
def update_document():
    request_form = request.form

    if "job_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: job_id not provided."}),
            status=400,
        )

    if "document_index" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: document_index not provided."}),
            status=400,
        )

    if "matricule" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: matricule not provided."}),
            status=400,
        )

    if "subquestion_predictions" not in request_form:
        return Response(
            response=json.dumps(
                {"response": f"Error: subquestion_predictions not provided."}
            ),
            status=400,
        )

    if "total" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: total not provided."}),
            status=400,
        )

    if "status" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: document_index not provided."}),
            status=400,
        )

    print(request_form)

    #
    job_id = str(request_form["job_id"])
    document_index = int(request_form["document_index"])
    matricule = str(request_form["matricule"])
    subquestion_predictions = json.loads(request_form["subquestion_predictions"])
    total = float(request_form["total"])
    status = Document_Status(str(request_form["status"]))

    #
    db = mongo_client["RMN"]
    collection = db["job_documents"]

    #
    collection.update_one(
        {"job_id": job_id, "document_index": document_index},
        {
            "$set": {
                "matricule": matricule,
                "subquestion_predictions": subquestion_predictions,
                "total": total,
                "status": Document_Status.VALIDATED.value,
            }
        },
    )

    return Response(response=json.dumps({"response": "OK"}), status=200)


@app.route("/document/download", methods=["POST"])
@cross_origin()
@verify_token()
def download_document():
    #
    request_form = request.form

    if "job_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: job_id not provided."}),
            status=400,
        )

    if "document_index" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: document_index not provided."}),
            status=400,
        )

    #
    job_id = str(request_form["job_id"])
    document_index = int(request_form["document_index"])

    #
    db = mongo_client["RMN"]
    document_collection = db["job_documents"]

    #
    document_file = document_collection.find_one(
        {"job_id": job_id, "document_index": document_index}
    )
    if document_file is None:
        return Response(
            response=json.dumps({"response": f"No document found!"}),
            status=404,
        )

    # Save file to local
    file_id = str(document_file["image_id"])
    print("file_id", file_id)
    storage.copy_from(file_id, file_id)
    file_send = send_file(file_id)

    time.sleep(0.1)

    @after_this_request
    def add_close_action(response):
        try:
            os.remove(file_id)
        except Exception as e:
            print(e)
        return response

    return file_send


@app.route("/job/validate", methods=["POST"])
@cross_origin()
@verify_token()
def validate():
    #
    request_form = request.form

    #
    if "job_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: job_id not provided."}),
            status=400,
        )
    if "user_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: user_id not provided."}),
            status=400,
        )

    if "moodle_ind" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: moodle_ind not provided."}),
            status=400,
        )

    #
    job_id = str(request_form["job_id"])
    user_id = str(request_form["user_id"])
    moodle_ind = request_form["moodle_ind"]

    db = mongo_client["RMN"]
    collection = db["job_documents"]
    collection_eval_jobs = db["eval_jobs"]

    # Set Job status to VALIDATION
    collection_eval_jobs.update_one(
        {"job_id": job_id}, {"$set": {"job_status": Job_Status.VALIDATING.value}}
    )

    # Create SocketIO connection
    sio = socketio.Client()
    sio.connect(f"http://{socketio_host}:7000")

    sio.emit(
        "jobs_status",
        json.dumps(
            {
                "job_id": job_id,
                "status": Job_Status.VALIDATING.value,
                "user_id": user_id,
            }
        ),
    )

    # add to Redis Queue
    queue_object = {
        "job_type": "validation",
        "job_id": job_id,
        "user_id": user_id,
        "moodle_ind": moodle_ind,
    }
    try:
        r.rpush("job_queue", json.dumps(queue_object))
    except Exception as e:
        print(e)
        print("Failed to push job to Redis Queue.")
        return Response(
            response=json.dumps(
                {"response": f"Error: Failed to push job to Redis Queue."}
            ),
            status=500,
        )

    # set all estimation to 0
    collection.update_many(
        {"job_id": job_id},
        {
            "$set": {
                "execution_time": 0,
            }
        },
    )

    return Response(response=json.dumps({"response": "OK"}), status=200)


def delete_job(job_id):
    print("Delete job:", job_id)

    try:
        storage.remove(f"output_csv/{job_id}.csv")
    except Exception as e:
        print(e)
    try:
        storage.remove(f"csv/{job_id}.csv")
    except Exception as e:
        print(e)
    try:
        storage.remove(f"output_zip/{job_id}*.zip")
    except Exception as e:
        print(e)
    try:
        storage.remove(f"zips/{job_id}.zip")
    except Exception as e:
        print(e)
    try:
        storage.remove_tree(f"documents/{job_id}")
    except Exception as e:
        print(e)
    try:
        storage.remove_tree(f"unverified_numbers/{job_id}")
    except Exception as e:
        print(e)

    #
    db = mongo_client["RMN"]
    collection = db["job_documents"]
    collection_eval_jobs = db["eval_jobs"]
    collection_output = db["jobs_output"]

    #
    try:
        collection.delete_many({"job_id": job_id})
    except Exception as e:
        print(e)

    #
    try:
        collection_eval_jobs.delete_many({"job_id": job_id})
    except Exception as e:
        print(e)

    try:
        collection_output.delete_many({"job_id": job_id})
    except Exception as e:
        print(e)


@app.route("/job/delete", methods=["POST"])
@cross_origin()
@verify_token()
def delete():
    request_form = request.form

    if "job_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: job_id not provided."}),
            status=400,
        )

    #
    job_id = str(request_form["job_id"])
    delete_job(job_id)

    #
    return Response(response=json.dumps({"response": "OK"}), status=200)


def delete_old_jobs(n_days_old = 0, user_id = None):
    db = mongo_client["RMN"]
    collection = db["eval_jobs"]
    r = {} if user_id is None else {"user_id": user_id}
    jobs = collection.find(r)

    now = datetime.utcnow()
    n = 0
    for j in jobs:
        delta = now - j["queued_time"]
        if delta.days >= n_days_old:
            delete_job(j["job_id"])
            n = n + 1

    return n


@app.route("/admin/delete/jobs", methods=["POST"])
@cross_origin()
def admin_delete_jobs():
    request_form = request.form

    if "n_days_old" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: n_days_old not provided."}),
            status=400,
        )

    #
    n_days_old = int(request_form["n_days_old"])

    user_id = None
    if "username" in request_form:
        user_id = str(request_form["username"])
    elif "user_id" in request_form:
        user_id = str(request_form["user_id"])

    n = delete_old_jobs(n_days_old, user_id)

    #
    return Response(response=json.dumps({"response": "OK", "n_deleted_jobs": n}), status=200)


@app.route("/admin/signup", methods=["POST"])
@cross_origin()
def admin_signup():
    db = mongo_client["RMN"]
    return UserService.signup(request, db)


@app.route("/admin/delete/tokens", methods=["POST"])
@cross_origin()
def admin_delete_tokens():
    request_form = request.form
    user_id = None
    if "username" in request_form:
        user_id = str(request_form["username"])
    elif "user_id" in request_form:
        user_id = str(request_form["user_id"])
    n_days_old = int(request_form["n_days_old"]) if "n_days_old" in request_form else 0
    db = mongo_client["RMN"]
    UserService.delete_tokens(user_id, n_days_old, db)
    return Response(
        response=json.dumps({"response": "OK"}),
        status=200
    )

@app.route("/admin/delete/user", methods=["POST"])
@cross_origin()
def admin_delete_user():
    request_form = request.form

    if "username" not in request_form and "user_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: username and user_id not provided. Please one of these two fields."}),
            status=400,
        )

    if "username" in request_form:
        user_id = str(request_form["username"])
    else:
        user_id = str(request_form["user_id"])
    #
    delete_old_jobs(user_id=user_id)

    #
    db = mongo_client["RMN"]
    TemplateService.delete_templates(user_id, db, storage)
    UserService.delete(user_id, db)

    #
    return Response(response=json.dumps({"response": "OK"}), status=200)


@app.route("/admin/users", methods=["POST"])
@cross_origin()
def admin_users():
    db = mongo_client["RMN"]
    all_users = UserService.users(db)
    return Response(response=json.dumps({"response": "OK", "users": all_users}), status=200)


@app.route("/admin/change_password", methods=["POST"])
@cross_origin()
def admin_change_password():
    db = mongo_client["RMN"]
    return UserService.change_password(request, db, False)


@app.route("/front_page", methods=["POST"])
@cross_origin()
@verify_token()
def front_page():
    request_form = request.form

    if "user_id" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: user_id not provided."}),
            status=400,
        )

    if "suffix" not in request_form:
        return Response(
            response=json.dumps({"response": f"Error: suffix not provided."}),
            status=400,
        )

    if not request.files:
        return Response(
            response=json.dumps({"response": f"Error: No files provided."}),
            status=400,
        )

    if "moodle_zip" not in request.files:
        return Response(
            response=json.dumps({"response": f"Error: moodle_zip file not provided."}),
            status=400,
        )

    if "latex_front_page" not in request.files:
        return Response(
            response=json.dumps(
                {"response": f"Error: latex_front_page file not provided."}
            ),
            status=400,
        )


    user_id = str(request_form["user_id"])
    suffix = str(request_form["suffix"])
    moodle_zip = request.files.get("moodle_zip")
    latex_front_page = request.files.get("latex_front_page")

    print(user_id)
    print(suffix)

    if not os.path.exists(FRONT_PAGE_TEMP_FOLDER):
        os.makedirs(FRONT_PAGE_TEMP_FOLDER)

    current_temp_folder = FRONT_PAGE_TEMP_FOLDER.joinpath(user_id)

    if not os.path.exists(current_temp_folder):
        os.makedirs(current_temp_folder)

    moodle_zip_name = secure_filename(moodle_zip.filename)
    latex_front_page_name = secure_filename(latex_front_page.filename)

    # Copy latex_input_file in temp_folder
    shutil.copy(LATEX_INPUT_FILE, current_temp_folder)

    moodle_zip_filepath = str(current_temp_folder.joinpath(moodle_zip_name))
    latex_front_page_filepath = str(current_temp_folder.joinpath(latex_front_page_name))
    latex_input_file_filepath = str(current_temp_folder.joinpath("data.tex"))

    with open(moodle_zip_filepath, "wb") as f_out:
        file_content = moodle_zip.stream.read()
        f_out.write(file_content)

    content_temp_folder = current_temp_folder.joinpath("moodle")
    if not os.path.exists(content_temp_folder):
        os.makedirs(content_temp_folder)

    shutil.unpack_archive(moodle_zip_filepath, content_temp_folder)
    os.remove(moodle_zip_filepath)

    latex_front_page.save(FileIO(latex_front_page_filepath, "wb"))

    handler = FrontPageHandler()
    handler.addFrontPages(
        str(current_temp_folder),
        content_temp_folder,
        suffix,
        latex_front_page_filepath,
        latex_input_file_filepath,
    )

    shutil.make_archive(str(content_temp_folder), "zip", content_temp_folder)

    file_send = send_file(f"{str(content_temp_folder)}.zip")

    shutil.rmtree(str(current_temp_folder))

    return file_send


if __name__ == "__main__":
    app.run(debug=True)
