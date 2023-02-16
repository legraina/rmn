from flask import Flask, request, Response, json, send_file
from utils.box_converter import convert_box_to_dict, convert_box_to_list
from pathlib import Path
from io import FileIO
from werkzeug.utils import secure_filename
import uuid
import os


TEMP_FOLDER = Path(__file__).resolve().parent.joinpath("temp")


class TemplateService() :

    def create_template(request, db, storage) :

        request_form = request.form

        if "user_id" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: user_id not provided."}),
                status=400,
            )

        if "grade_box" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: matricule_box not provided."}),
                status=400,
            )

        template_name = request_form['template_name'] if "template_name" in request_form else "Template"
        print(request_form['matricule_box'])
        matricule_box = convert_box_to_list(json.loads(request_form['matricule_box'])) if "matricule_box" in request_form else None
        grade_box = convert_box_to_list(json.loads(request_form['grade_box'])) if "grade_box" in request_form else None

        print(request.files)

        if not request.files:
            return Response(
                response=json.dumps({"response": f"Error: No file provided."}),
                status=400,
            )

        if "template_file" not in request.files:
            return Response(
                response=json.dumps({"response": f"Error: Template file not provided."}),
                status=400,
            )

        user_id = str(request_form["user_id"])

        if not os.path.exists(TEMP_FOLDER):
            os.makedirs(TEMP_FOLDER)
        try:
            template_file = request.files.get("template_file")
            template_file_name = secure_filename(template_file.filename)
            template_file.save(FileIO(TEMP_FOLDER.joinpath(template_file_name), "wb"))

        except Exception as e:
            print(e)
            return Response(response=f"Error: Failed to download files.", status=900)


        # Define db and collection used
        collection = db["template"]

        template_id = str(uuid.uuid4())

        try:
            file_name = str(TEMP_FOLDER.joinpath(template_file_name))
            path_on_cloud = 'template/'
            template_file_id = f'{path_on_cloud}{template_id}.pdf'
            storage.move_to(file_name, template_file_id)

        except Exception as e:
            print(e)
            return Response(
                response=json.dumps({"response": f"Error: Failed to upload files to storage."}),
                status=500,
            )

        template = {
            "user_id": user_id,
            "template_id": template_id,
            "template_name": str(template_name),
            "matricule_box": matricule_box,
            "grade_box": grade_box,
            "template_file_id": template_file_id
        }

        try:
            collection.insert_one(template)
        except Exception as e:
            print(e)
            return Response(
                response=json.dumps({"response": f"Error: Failed to insert in MongoDB."}),
                status=500,
            )

        return Response(response=json.dumps({"response": "OK"}), status=200)


    def delete_template(request, db, storage):
        request_form = request.form

        if "template_id" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: template_id not provided."}),
                status=400,
            )

        template_id = str(request_form["template_id"])
        collection = db["template"]
        storage.remove(f'template/{template_id}.pdf')
        collection.delete_one({"template_id": template_id})

        return Response(response=json.dumps({"response": "OK"}), status=200)

    def delete_templates(user_id, db, storage):
        collection = db["template"]
        templates = collection.find({"user_id": user_id})
        for t in templates:
            t_id = t["template_id"]
            storage.remove(f'template/{t_id}.pdf')
        collection.delete_many({"user_id": user_id})

    def get_all_template_info(request, db) :
        request_form = request.form

        if "user_id" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: user_id not provided."}),
                status=400,
            )


        user_id = str(request_form["user_id"])

        if not os.path.exists(TEMP_FOLDER):
            os.makedirs(TEMP_FOLDER)


        # Define db and collection used

        collection = db["template"]

        templates = collection.find({"user_id": user_id})

        user_templates_list = [
            {
            "template_name": template['template_name'],
            "template_id": template['template_id']
            }
            for template in templates
        ]

        return Response(response=json.dumps({"response": user_templates_list}), status=200)

    def get_template_info(request, db) :
        request_form = request.form

        if "template_id" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: template_id not provided."}),
                status=400,
            )


        template_id = str(request_form["template_id"])

        if not os.path.exists(TEMP_FOLDER):
            os.makedirs(TEMP_FOLDER)


        # Define db and collection used

        collection = db["template"]

        template = collection.find_one({"template_id": template_id})

        template_resp = {
            "template_name": template['template_name'],
            "template_id": template['template_id'],
            "matricule_box" :convert_box_to_dict(template['matricule_box']) if 'matricule_box' in template else None,
            "grade_box" :convert_box_to_dict(template['grade_box']) if 'grade_box' in template else None,
        }

        return Response(response=json.dumps({"response": template_resp}), status=200)

    def download_template_file(request, db, storage) :
        request_form = request.form

        #
        if "template_id" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: template_id not provided."}),
                status=400,
            )

        template_id = str(request_form["template_id"])

        # Save file to local
        filepath = str(TEMP_FOLDER.joinpath(template_id))
        storage.copy_from(f"template/{template_id}.pdf", filepath)
        print("file created")

        file_send = send_file(filepath)

        os.remove(filepath)

        return file_send

    def change_template_info(request, db) :
        request_form = request.form


        # if not request_form.keys() & { "template_id", "template_name", "matricule_box", "grade_box"}:
        #     return Response(
        #         response=json.dumps({"response": f"Error: Missing value in request form"}),
        #         status=400,
        #     )

        template_name = request_form['template_name']
        matricule_box = convert_box_to_list(json.loads(request_form['matricule_box']))
        grade_box = convert_box_to_list(json.loads(request_form['grade_box']))

        template_id = str(request_form["template_id"])

        collection = db["template"]

        collection.update_one(
            {"template_id": template_id},
            {
                "$set": {
                    "template_name": template_name,
                    "matricule_box": matricule_box,
                    "grade_box": grade_box,
                }
            })

        return Response(response=json.dumps({"response": "OK"}), status=200)
