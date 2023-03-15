import redis
import configparser
from pymongo import MongoClient
from pathlib import Path
from python.process_copy.parser import parse_run_args
from python.process_copy.recognize import get_date
from python.process_copy.config import MoodleFields as MF
from utils.utils import Job_Status, Document_Status
from utils.storage import Storage
from utils.stop_handler import StopHandler
from zipfile import ZipFile
import socketio

import subprocess
import os
import shutil
import json
import pandas as pd
import uuid
import time
from datetime import datetime, timedelta


ROOT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = ROOT_DIR.joinpath("config").joinpath("config.ini")
parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
parser.read(CONFIG_FILE)
MAX_RETRY = int(os.getenv("MAX_RETRY", "5"))

mongo_url = parser.get("MONGODB", "URL")
redis_host = "redis" if os.getenv("ENVIRONNEMENT") == "production" else "localhost"
socketio_host = (
    "socketio" if os.getenv("ENVIRONNEMENT") == "production" else "localhost"
)

storage = Storage()


def save_number_images(job_id, document_index, questions):
    try:
        numbers = [n for n in questions.values()]

        for index, number in enumerate(numbers):
            number = float(number)
            if number.is_integer() and 0 <= int(number) <= 9:
                try:
                    unverified_filename = f"unverified_numbers/{job_id}/{document_index}/{index}.png"
                    new_filename = f"numbers/{int(number)}/{uuid.uuid4()}.png"
                    storage.move_to(storage.abs_path(unverified_filename), new_filename)
                except Exception as e:
                    print(e)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    # Connect to Mongo
    print("Setting up MongoClient...")
    mongo_client = MongoClient(mongo_url)

    db = mongo_client["RMN"]
    collection = db["job_documents"]
    collection_eval_jobs = db["eval_jobs"]
    collection_output = db["jobs_output"]
    collection_user = db["users"]

    # Create SocketIO connection
    sio = socketio.Client()
    sio.connect(f"http://{socketio_host}:7000")

    # create redis connection
    r = redis.Redis(host=redis_host, port=6379, db=0)

    def process(p_job, TMP_DIR):
        job_id = p_job["job_id"]
        user_id = p_job["user_id"]
        job_type = p_job["job_type"]

        MOODLE_ZIP = TMP_DIR.joinpath("moodle.zip")
        MOODLE_FOLDER = TMP_DIR.joinpath("moodle")
        OUTPUT_FOLDER = TMP_DIR.joinpath("output")
        EXTRACT_FOLDER = TMP_DIR.joinpath("extract")
        VALIDATE_FOLDER = TMP_DIR.joinpath("validate")

        stopH = StopHandler(collection_eval_jobs, job_id)

        if job_type == "validation":
            moodle_ind = bool(int(p_job["moodle_ind"]))
            #
            user = collection_user.find_one({"username": user_id})
            save_verified_images = user["saveVerifiedImages"]

            #
            output = collection_output.find_one({"job_id": job_id})
            notes_csv_file_id = output["notes_csv_file_id"]
            moodle_zip_id_list = output["moodle_zip_id_list"]

            #
            VALIDATE_FOLDER.mkdir(exist_ok=True)
            tmp_copies_folder_path = VALIDATE_FOLDER.joinpath("copies")
            tmp_copies_folder_path.mkdir(exist_ok=True)
            validated_copies_folder_path = VALIDATE_FOLDER.joinpath(
                "validated_copies"
            )
            validated_copies_folder_path.mkdir(exist_ok=True)

            # Save file to local
            csv_file_path = str(VALIDATE_FOLDER.joinpath('notes.csv'))
            storage.copy_from(notes_csv_file_id, csv_file_path)
            print("notes.csv file created")

            #
            df = pd.read_csv(csv_file_path, index_col=MF.mat, dtype={MF.mat: str})

            # check if group or gr column is present
            group_label = None
            group_df = df.filter(regex='(?i)(gr|groupe?s?)$')
            if group_df.shape[1] == 1:
                group_label = group_df.columns[0]

            #
            docs = collection.find({"job_id": job_id})

            #
            print(f"Col: {df.columns}")
            dt = get_date()
            for document_index, doc in enumerate(docs):
                mat = str(doc["matricule"])
                if mat in df.index.values:
                    for key in doc["subquestion_predictions"].keys():
                        df.loc[mat, key] = doc["subquestion_predictions"][key]
                    df.loc[mat, MF.grade] = doc["total"]
                    df.loc[mat, MF.mdate] = dt
            df.to_csv(csv_file_path, mode="w+")

            #
            collection.update_many(
                {"job_id": job_id},
                {
                    "$set": {
                        "status": Document_Status.VALIDATED.value,
                    }
                },
            )

            counter = 0
            all_copies_folder_path = validated_copies_folder_path.joinpath("all")
            all_copies_folder_path.mkdir(exist_ok=True)
            print("All folder:", str(all_copies_folder_path))
            for i, id in enumerate(moodle_zip_id_list):
                # moodle_i
                moodle_folder_name = f"moodle_{i}"
                moodle_folder_path = validated_copies_folder_path.joinpath(moodle_folder_name)
                moodle_folder_path.mkdir(exist_ok=True)

                # moodle_i.zip
                moodle_filename = f"{moodle_folder_name}.zip"
                # validated_tmp_folder/<job_id>_moodle_0.zip
                file_p = str(VALIDATE_FOLDER.joinpath(moodle_filename))
                storage.copy_from(id, file_p)
                # validated_tmp_folder/copies/[1.pdf, 2.pdf]
                shutil.unpack_archive(file_p, tmp_copies_folder_path)
                curr_moodle_folder_path = tmp_copies_folder_path

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

                        if doc is None:
                            continue

                        doc_idx = doc["document_index"]
                        n_total_doc = doc["n_total_doc"]

                        start_time = time.time()

                        if save_verified_images:
                            save_number_images(
                                job_id, doc_idx - 1, doc["subquestion_predictions"]
                            )

                        matricule = str(doc["matricule"])
                        try:
                            nom_complet = df.at[matricule, MF.name]
                        except Exception as e:
                            print(e)
                            print("Matricule", matricule, "not found in csv.")
                            continue

                        try:
                            nom, prenom = nom_complet.split()
                        except Exception as e:
                            print(nom_complet)
                            print(e)
                            nom = nom_complet
                            prenom = ""

                        if moodle_ind:
                            # create folder
                            identifiant = df.at[matricule, MF.id]
                            folder_name = f"{nom_complet}_{identifiant}_{matricule}_assignsubmission_file_"
                            print("folder name", folder_name)
                            m_folder = moodle_folder_path.joinpath(folder_name)
                            m_folder.mkdir(exist_ok=True)
                            print("folder path", str(m_folder))

                            m_dest = m_folder.joinpath(f"{nom}_{prenom}_{matricule}.pdf")
                            print("destination", m_dest)

                            # transfert file to folder
                            shutil.copy(str(file), str(m_dest))

                        copies_path = all_copies_folder_path
                        if group_label:
                            group = df.at[matricule, group_label]
                            copies_path = copies_path.joinpath(str(group))
                            copies_path.mkdir(exist_ok=True)
                        dest = copies_path.joinpath(f"{nom}_{prenom}_{matricule}.pdf")
                        os.rename(str(file), str(dest))

                        exec_time = time.time() - start_time
                        counter += 1

                        collection.update_one(
                            {
                                "job_id": job_id,
                                "document_index": doc_idx,
                                "status": Document_Status.VALIDATED.value,
                            },
                            {
                                "$set": {
                                    "document_index": counter,
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
                                    "document_index": counter,
                                    "execution_time": exec_time,
                                    "status": Document_Status.READY.value,
                                    "n_total_doc": n_total_doc,
                                }
                            ),
                        )

                #
                if moodle_ind:
                    shutil.make_archive(
                        str(VALIDATE_FOLDER.joinpath(moodle_folder_name)),
                        "zip",
                        str(moodle_folder_path)
                    )

                    try:
                        c_zip = str(VALIDATE_FOLDER.joinpath(moodle_filename))
                        storage.move_to(c_zip, id)
                    except Exception as e:
                        print(e)
                else:
                    storage.remove(id)

            # create zip with all copies (gathered by group if enabled)
            shutil.make_archive(
                str(VALIDATE_FOLDER.joinpath("all")),
                "zip",
                str(all_copies_folder_path)
            )
            zip_file_id = f"output_zip/{job_id}_all.zip"
            try:
                all_zip_name = str(VALIDATE_FOLDER.joinpath("all"))
                c_zip = f"{all_zip_name}.zip"
                storage.move_to(c_zip, zip_file_id)
            except Exception as e:
                print(e)

            # update zip list
            zip_id_list = [zip_file_id]
            if moodle_ind:
                zip_id_list += moodle_zip_id_list

            if stopH.stop():
                print("Job has been deleted.")
                return

            try:
                n_csv = f"output_csv/{job_id}.csv"
                storage.move_to(csv_file_path, n_csv)

                #
                collection_output.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "notes_csv_file_id": notes_csv_file_id,
                        "moodle_zip_id_list": zip_id_list
                    }})

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
            except Exception as e:
                print("Error while moving file to storage")
                collection_eval_jobs.update_one(
                    {"job_id": job_id},
                    {
                        "$set": {
                            "job_status": Job_Status.ERROR.value,
                        }
                    },
                )

            # delete preview image
            print("Clean documents and unverified_numbers")
            docs = collection.find({"job_id": job_id})
            for doc in docs:
                # delete unverified numbers for job
                document_index = doc["document_index"] - 1
                for image_index in range(len(doc["subquestion_predictions"].keys())):
                    try:
                        storage.remove(f"unverified_numbers/{job_id}/{document_index}/{image_index}.png")
                    except:
                        continue

            try:
                storage.remove_tree(f"documents/{job_id}")
            except:
                pass

            collection.delete_many({"job_id": job_id})

        elif job_type == "execution":
            # make directories
            MOODLE_FOLDER.mkdir(exist_ok=True)
            OUTPUT_FOLDER.mkdir(exist_ok=True)
            EXTRACT_FOLDER.mkdir(exist_ok=True)

            # Query job params
            print("Querying job details from Database...")
            job_params = collection_eval_jobs.find_one({"job_id": job_id})

            if job_params is None:
                print("No params found!")
                return

            print(job_params)

            # Save notes.csv file to local
            storage.copy_from(job_params["notes_file_id"], str(OUTPUT_FOLDER.joinpath("notes.csv")))

            # Save zip file to local
            storage.copy_from(job_params["zip_file_id"], str(OUTPUT_FOLDER.joinpath("content.zip")))

            with ZipFile(str(OUTPUT_FOLDER.joinpath("content.zip")), "r") as zip_ref:
                zip_ref.extractall(EXTRACT_FOLDER)

            args = [
                str(EXTRACT_FOLDER),
                "-m",
                str(MOODLE_FOLDER),
                "-g",
                "exam",
                "--grades",
                str(OUTPUT_FOLDER.joinpath("notes.csv")),
                "-e",
                "--job_id",
                job_id,
                "--user_id",
                user_id,
                "--template_id",
                job_params["template_id"],
                "--export",
                "--batch",
                "500",
            ]
            print("Running module with:", args)
            # process_copy
            try:
                parse_run_args(args)
            except Exception as e:
                print("Error in process-copy:", e)

                if stopH.stop():
                    print("Job has been deleted.")
                    storage.remove(f"csv/{job_id}.csv")
                    storage.remove(f"zips/{job_id}.zip")
                    return

                # check if should retry
                retry = job_params.get("retry", 0)
                if retry < MAX_RETRY:
                    raise e

                # Error handling
                collection_eval_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {"job_status": Job_Status.ERROR.value}}
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

                storage.remove(f"csv/{job_id}.csv")
                storage.remove(f"zips/{job_id}.zip")
                return

            print("Module Done")

            # Save output files in storage
            folder = "output_csv/"
            filename = f"{job_id}.csv"
            notes_csv_file_id = f"{folder}{filename}"
            storage.move_to(str(OUTPUT_FOLDER.joinpath("notes.csv")), notes_csv_file_id)

            folder = "output_zip/"
            filename = f"{job_id}.zip"
            moodle_zip_file_id = f"{folder}{filename}"
            storage.move_to(str(MOODLE_ZIP), moodle_zip_file_id)

            moodle_zip_id_list = [moodle_zip_file_id]
            i = 1
            for file_path in TMP_DIR.glob("moodle*.zip"):
                moodle_zip_file_id = f"{folder}{job_id}_{i}.zip"
                storage.move_to(str(file_path), moodle_zip_file_id)
                moodle_zip_id_list.append(moodle_zip_file_id)
                i = i + 1

            collection_output.insert_one(
                {
                    "job_id": job_id,
                    "notes_csv_file_id": notes_csv_file_id,
                    "preview_file_id": "None",
                    "moodle_zip_id_list": moodle_zip_id_list,
                }
            )

            # Set Job status to VALIDATION
            collection_eval_jobs.update_one(
                {"job_id": job_id}, {"$set": {"job_status": Job_Status.VALIDATION.value}}
            )

            sio.emit(
                "jobs_status",
                json.dumps(
                    {
                        "job_id": job_id,
                        "status": Job_Status.VALIDATION.value,
                        "user_id": user_id,
                    }
                ),
            )

            storage.remove(f"csv/{job_id}.csv")
            storage.remove(f"zips/{job_id}.zip")
        else:
            print(f"Type '{job_type}' not handled.")

    try:
        # retrieve job
        print("Retrieving job from redis")
        job = r.lpop("job_queue")

        # process job if any
        if job:
            print("Job:", job)
            job = json.loads(job)
            # create tmp work dir
            job_id = job["job_id"]
            WORK_TMP_DIR = ROOT_DIR.joinpath(f"tmp_{job_id}")
            WORK_TMP_DIR.mkdir(exist_ok=True)
            # process job
            try:
                process(job, WORK_TMP_DIR)
            except:
                pass
            # clean
            shutil.rmtree(WORK_TMP_DIR)

        # check if any job is idle and dangling
        print("Check idle running jobs")
        alive_times = {}
        while True:
            # search idle jobs
            max_alive = datetime.utcnow() - timedelta(seconds=120)
            jobs = collection_eval_jobs.find({
                "job_status": Job_Status.RUN.value,
                "alive_time": {"$lt": max_alive},
                "retry": {"$lt": MAX_RETRY + 1}
            })
            # requeue idle jobs
            idle_jobs = False
            for j in jobs:
                print("Resubmit job", j["job_id"])
                # change status to ensure that a job is not resubmitted several times
                res = collection_eval_jobs.update_one(
                    {"job_id": j["job_id"], "job_status": Job_Status.RUN.value},
                    {"$inc": {"retry": 1}, "$set": {"job_status": Job_Status.QUEUED.value}}
                )
                if res.matched_count > 0:
                    d_json = {
                        "user_id": j["user_id"],
                        "job_id": j["job_id"],
                        "job_type": "execution"
                    }
                    r.lpush("job_queue", json.dumps(d_json))
                idle_jobs = True

            # continue if idle jobs
            if idle_jobs:
                break

            # check if any job is running. If yes, sleep, otherwise break
            jobs = collection_eval_jobs.find({
                "job_status": Job_Status.RUN.value,
                "retry": {"$lt": MAX_RETRY + 1}
            })
            one_job_alive = False
            for j in jobs:
                job_id = j["job_id"]
                alive_t = alive_times.get(job_id, datetime.utcnow())
                # check if alive_time has increased, and thus job is alived
                if j["alive_time"] > alive_t:
                    one_job_alive = True
                    break
                alive_times[job_id] = j["alive_time"]
            # if one job alive -> stop
            if one_job_alive:
                break
            # otherwise, sleep
            time.sleep(5)

    except Exception as e:
        print(e)

    print("Job end.")

    mongo_client.close()
    sio.disconnect()
