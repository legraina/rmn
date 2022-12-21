import redis
import configparser
from pymongo import MongoClient
from pathlib import Path
from utils.utils import Job_Status, Document_Status
from zipfile import ZipFile
import socketio

import subprocess
import os
import shutil
import json
import pandas as pd
import uuid
import time

import pyrebase

firebaseConfig = {
    "apiKey": "AIzaSyAPHNsT4BQjbvC_NNgu0BB3YXPZy1vioNU",
    "authDomain": "projet4-bcfe5.firebaseapp.com",
    "projectId": "projet4-bcfe5",
    "storageBucket": "projet4-bcfe5.appspot.com",
    "messagingSenderId": "171342986362",
    "appId": "1:171342986362:web:018b05e620c609a2ce0fc3",
    "measurementId": "G-E9P71RH1DF",
    "databaseURL": "",
    "serviceAccount": "./config/projet4_service_account.json",
}

FOLDER = "zip_extract"

MOODLE_ZIP = Path(__file__).resolve().parent.joinpath("moodle.zip")

MOODLE_FOLDER = Path(__file__).resolve().parent.joinpath("moodle")

CONFIG_FILE = Path(__file__).resolve().parent.joinpath("config").joinpath("config.ini")

OUTPUT_FOLDER = Path(__file__).resolve().parent.joinpath("output")

# PREVIEW_OUTPUT_FILE = Path(__file__).resolve().parent.joinpath("notes_summary.pdf")

TEMP_FOLDER = Path(__file__).resolve().parent.joinpath("temp")

VALIDATE_TEMP_FOLDER = Path(__file__).resolve().parent.joinpath("validate_temp_folder")


parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
parser.read(CONFIG_FILE)

URL = parser.get("MONGODB", "URL")

redis_host = "redis" if os.getenv("ENVIRONNEMENT") == "production" else "localhost"
socketio_host = (
    "socketio" if os.getenv("ENVIRONNEMENT") == "production" else "localhost"
)


def save_number_images(job_id, document_index, questions):
    numbers = [n for n in questions.values()]

    firebase_storage = pyrebase.initialize_app(firebaseConfig).storage()

    for index, number in enumerate(numbers):
        number = float(number)
        if number.is_integer() and 1 <= int(number) <= 9:
            filename = f"{uuid.uuid4()}.png"

            open("unverified_number.png", "w+")

            filepath = "unverified_number.png"
            firebase_storage.child(
                f"unverified_numbers/{job_id}/{document_index}/{index}.png"
            ).download(filepath)
            firebase_storage.child(f"numbers/{int(number)}/{filename}").put(filepath)

            os.remove("unverified_number.png")


if __name__ == "__main__":

    r = redis.Redis(host=redis_host, port=6379, db=0)
    job = r.lpop("job_queue")

    if not job:
        print("No job! Exiting...")
        exit()

    queue_object = json.loads(job)
    job_type = queue_object["job_type"]

    #
    print("Setting up MongoClient...")
    mongo_client = MongoClient(URL)

    db = mongo_client["RMN"]
    collection = db["job_documents"]
    collection_eval_jobs = db["eval_jobs"]
    collection_output = db["jobs_output"]
    collection_user = db["users"]

    # Create SocketIO connection
    sio = socketio.Client()
    sio.connect(f"http://{socketio_host}:7000")

    firebase_storage = pyrebase.initialize_app(firebaseConfig).storage()

    if job_type == "validation":
        #
        job_id = queue_object["job_id"]
        user_id = queue_object["user_id"]
        moodle_ind = bool(int(queue_object["moodle_ind"]))

        #
        user = collection_user.find_one({"username": user_id})
        save_verified_images = user["saveVerifiedImages"]

        #
        output = collection_output.find_one({"job_id": job_id})
        notes_csv_file_id = output["notes_csv_file_id"]
        moodle_zip_id_list = output["moodle_zip_id_list"]

        #
        validate_tmp_folder_path = VALIDATE_TEMP_FOLDER.joinpath(f"{job_id}")
        temp_copies_folder_path = validate_tmp_folder_path.joinpath("copies")
        validated_copies_folder_path = validate_tmp_folder_path.joinpath(
            "validated_copies"
        )

        # download files
        if not os.path.exists(validate_tmp_folder_path):
            os.makedirs(validate_tmp_folder_path)

        # Save file to local
        filename = f"{job_id}_notes.csv"
        file_path = str(validate_tmp_folder_path.joinpath(filename))
        firebase_storage.child(notes_csv_file_id).download(file_path)
        print("notes.csv file created")

        #
        df = pd.read_csv(file_path, index_col="Matricule", dtype={"Matricule": str})

        #
        docs = collection.find({"job_id": job_id})

        #
        print(f"Docs: {docs}")
        print(f"index: {df.index.tolist()}")
        print(f"Col: {df.columns}")

        for document_index, doc in enumerate(docs):
            print(f'{doc["matricule"]}')
            if str(doc["matricule"]) in df.index.values:
                for key in doc["subquestion_predictions"].keys():
                    df.loc[str(doc["matricule"]), key] = doc["subquestion_predictions"][
                        key
                    ]
                df.loc[str(doc["matricule"]), "Note"] = doc["total"]

        #
        counter = 0

        collection.update_many(
            {"job_id": job_id},
            {
                "$set": {
                    "status": Document_Status.VALIDATED.value,
                }
            },
        )

        for i, id in enumerate(moodle_zip_id_list):
            #
            if not os.path.exists(temp_copies_folder_path):
                os.makedirs(temp_copies_folder_path)

            if not os.path.exists(validated_copies_folder_path):
                os.makedirs(validated_copies_folder_path)

            # <job_id>_moodle_0
            moodle_folder_name = f"{job_id}_moodle_{i}"
            # <job_id>_moodle_0.zip
            filename = f"{moodle_folder_name}.zip"
            # validated_tmp_folder/<job_id>_moodle_0.zip
            file_p = str(validate_tmp_folder_path.joinpath(filename))
            firebase_storage.child(id).download(file_p)
            # validated_tmp_folder/copies/[1.pdf, 2.pdf]
            shutil.unpack_archive(file_p, temp_copies_folder_path)
            curr_moodle_folder_path = temp_copies_folder_path

            if len(os.listdir(str(curr_moodle_folder_path))) == 0:
                continue

            for root, dirs, files in os.walk(str(curr_moodle_folder_path)):
                for f in files:
                    file = os.path.join(root, f)

                    print("file", str(file))

                    if (
                        not os.path.isfile(file)
                        or not f.endswith(".pdf")
                        or f.startswith(".")
                    ):
                        continue

                    doc = collection.find_one({"job_id": job_id, "filename": str(f)})
                    print("doc", doc)

                    if not doc:
                        continue

                    doc_idx = doc["document_index"]
                    n_total_doc = doc["n_total_doc"]

                    start_time = time.time()

                    if save_verified_images:
                        save_number_images(
                            job_id, doc_idx - 1, doc["subquestion_predictions"]
                        )

                    if moodle_ind:
                        # create folder
                        nom_complet = df.at[str(doc["matricule"]), "Nom complet"]
                        nom, prenom = nom_complet.split()
                        identifiant = df.at[str(doc["matricule"]), "Identifiant"]
                        matricule = str(doc["matricule"])
                        folder_name = f"{nom_complet}_{identifiant}_{matricule}_assignsubmission_file_"
                        print("folder name", folder_name)
                        folder = validated_copies_folder_path.joinpath(
                            moodle_folder_name
                        ).joinpath(folder_name)

                        print("folder path", str(folder))

                        if not os.path.exists(folder):
                            os.makedirs(folder)

                        dest = folder.joinpath(f"{nom}_{prenom}_{matricule}.pdf")

                        print("destination", dest)

                        # transfert file to folder
                        os.rename(str(file), str(dest))
                    else:
                        folder = validated_copies_folder_path.joinpath(
                            moodle_folder_name
                        )

                        if not os.path.exists(folder):
                            os.makedirs(folder)

                        nom_complet = df.at[str(doc["matricule"]), "Nom complet"]
                        nom, prenom = nom_complet.split()
                        matricule = str(doc["matricule"])

                        dest = folder.joinpath(f"{nom}_{prenom}_{matricule}.pdf")
                        os.rename(str(file), str(dest))

                    exec_time = time.time() - start_time

                    collection.update_one(
                        {
                            "job_id": job_id,
                            "document_index": doc_idx,
                            "status": Document_Status.VALIDATED.value,
                        },
                        {
                            "$set": {
                                "document_index": counter + 1,
                                "execution_time": exec_time,
                                "status": Document_Status.READY.value,
                            }
                        },
                    )

                    sio.emit(
                        "document_ready",
                        json.dumps(
                            {
                                "job_id": job_id,
                                "user_id": user_id,
                                "document_index": counter + 1,
                                "execution_time": exec_time,
                                "status": Document_Status.READY.value,
                                "n_total_doc": n_total_doc,
                            }
                        ),
                    )

                    counter += 1

            #
            shutil.make_archive(
                str(validate_tmp_folder_path.joinpath(moodle_folder_name)),
                "zip",
                str(validated_copies_folder_path.joinpath(moodle_folder_name)),
            )

            try:
                path_on_cloud = "output_zip/"
                firebase_storage.child(id).put(
                    str(validate_tmp_folder_path.joinpath(filename))
                )
            except Exception as e:
                print(e)

            shutil.rmtree(str(temp_copies_folder_path))
            shutil.rmtree(str(validated_copies_folder_path))

        #
        df.to_csv(file_path, mode="w+")

        try:
            path_on_cloud = "output_csv/"
            notes_csv_file_id = f"{path_on_cloud}{job_id}.csv"
            firebase_storage.child(notes_csv_file_id).put(file_path)
        except Exception as e:
            print("Error while inserting file to FireBase")
            collection_eval_jobs.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "job_status": Job_Status.ERROR.value,
                    }
                },
            )
            exit()

        #
        collection_output.update_one(
            {"job_id": job_id}, {"$set": {"notes_csv_file_id": notes_csv_file_id}}
        )

        #
        shutil.rmtree(str(validate_tmp_folder_path))

        #
        collection_eval_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "job_status": Job_Status.ARCHIVED.value,
                    "notes_file_id": notes_csv_file_id,
                }
            },
        )

        sio.emit(
            "jobs_status",
            json.dumps(
                {
                    "job_id": job_id,
                    "status": Job_Status.ARCHIVED.value,
                    "user_id": user_id,
                }
            ),
        )

        # delete preview image
        docs = collection.find({"job_id": job_id})

        for doc in docs:
            document_index = doc["document_index"] - 1
            try:
                firebase_storage.delete(f"documents/{job_id}_{document_index}.png")
            except:
                continue

            # delete unverified numbers for job
            for image_index in range(len(doc["subquestion_predictions"].keys())):
                try:
                    firebase_storage.delete(
                        f"unverified_numbers/{job_id}/{document_index}/{image_index}.png"
                    )
                except:
                    continue

        collection.delete_many({"job_id": job_id})

    elif job_type == "execution":
        job = queue_object["job_id"]
        user_id = queue_object["user_id"]

        # Query job params
        print("Querying job details from Database...")
        job_params = collection_eval_jobs.find_one({"job_id": job})
        print(job_params)

        if not job_params:
            print("No params found!")
            mongo_client.close()
            exit()

        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)

        # Save notes.csv file to local
        firebase_storage.child(job_params["notes_file_id"]).download(
            str(OUTPUT_FOLDER.joinpath("notes.csv"))
        )

        # Save zip file to local
        firebase_storage.child(job_params["zip_file_id"]).download(
            str(OUTPUT_FOLDER.joinpath("content.zip"))
        )

        if not os.path.exists(FOLDER):
            os.makedirs(FOLDER)

        with ZipFile(str(OUTPUT_FOLDER.joinpath("content.zip")), "r") as zip_ref:
            zip_ref.extractall(FOLDER)

        print("Running module")
        # process_copy
        proc = subprocess.Popen(
            [
                "python3",
                "-m",
                "python.process_copy",
                FOLDER,
                "-g",
                "exam",
                "--grades",
                str(OUTPUT_FOLDER.joinpath("notes.csv")),
                "-e",
                "--job_id",
                job,
                "--user_id",
                user_id,
                "--template_id",
                job_params["template_id"],
                "--export",
                "--batch",
                "500",
            ]
        )
        exit_code = proc.wait()

        # Error handling
        if exit_code != 0:
            collection_eval_jobs.update_one(
                {"job_id": job},
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
                        "job_id": job,
                        "user_id": user_id,
                        "status": Job_Status.ERROR.value,
                    }
                ),
            )
            print("Error in process-copy!")
            mongo_client.close()
            sio.disconnect()
            exit()

        print("Module Done")

        # Save output files in Firebase
        folder = "output_csv/"
        filename = f"{job}.csv"
        notes_csv_file_id = f"{folder}{filename}"
        firebase_storage.child(notes_csv_file_id).put(
            str(OUTPUT_FOLDER.joinpath("notes.csv"))
        )
        # folder = "output_preview/"
        # filename = f"{job}.pdf"
        # preview_file_id = f"{folder}{filename}"
        # firebase_storage.child(preview_file_id).put(str(PREVIEW_OUTPUT_FILE))

        folder = "output_zip/"
        filename = f"{job}.zip"
        moodle_zip_file_id = f"{folder}{filename}"
        firebase_storage.child(moodle_zip_file_id).put(str(MOODLE_ZIP))

        moodle_zip_id_list = [moodle_zip_file_id]
        for i in range(1, 1001):
            filename = f"{job}_{i}.zip"
            moodle_zip_file_id = f"{folder}{filename}"
            file_name = "moodle{0}.zip".format(i)
            if not os.path.isfile(file_name):
                break
            file_path = Path(__file__).resolve().parent.joinpath(file_name)
            firebase_storage.child(moodle_zip_file_id).put(str(file_path))
            moodle_zip_id_list.append(moodle_zip_file_id)

        collection_output.insert_one(
            {
                "job_id": job,
                "notes_csv_file_id": notes_csv_file_id,
                "preview_file_id": "None",
                "moodle_zip_id_list": moodle_zip_id_list,
            }
        )

        # Set Job status to VALIDATION
        collection_eval_jobs.update_one(
            {"job_id": job}, {"$set": {"job_status": Job_Status.VALIDATION.value}}
        )

        sio.emit(
            "jobs_status",
            json.dumps(
                {
                    "job_id": job,
                    "status": Job_Status.VALIDATION.value,
                    "user_id": user_id,
                }
            ),
        )

        firebase_storage.delete(f"csv/{job}.csv")
        firebase_storage.delete(f"zips/{job}.zip")

        # Clean up

        for i in range(1, 1001):
            file_name = "moodle{0}.zip".format(i)
            if not os.path.isfile(file_name):
                break
            file_path = Path(__file__).resolve().parent.joinpath(file_name)
            os.remove(file_path)

        # os.remove(PREVIEW_OUTPUT_FILE)
        shutil.rmtree(FOLDER)
        shutil.rmtree(OUTPUT_FOLDER)
        shutil.rmtree(MOODLE_FOLDER)
        os.remove(MOODLE_ZIP)

    else:
        print(f"Type '{job_type}' not handled.")

    mongo_client.close()
    sio.disconnect()
