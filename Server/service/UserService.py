from flask import Flask, request, Response, json, send_file
from werkzeug.security import generate_password_hash,check_password_hash


class UserService() :
        
    def login(request, database): 
        request_form = request.form
        if "username" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: username not provided."}),
                status=400,
            )

        if "password" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: password not provided."}),
                status=400,
            )
        username = request_form['username']
        password = request_form['password']
        collection = database["users"]
        userDB = collection.find_one({"username": username})
        if userDB is None : 
            return Response(
                response=json.dumps({"response": f"Nom d'utilisateur/Mot de passe invalide"}),
                status=404,
            )
        if check_password_hash(userDB['password'], password) :
            response = {
                    "username": userDB['username'],
                    "role": userDB['role'],
                    "saveVerifiedImages": userDB['saveVerifiedImages'],
                    "moodleStructureInd": userDB['moodleStructureInd']
                }

            return Response(
                response=json.dumps({"response": response}),
                status=200
                )

        return Response(
                response=json.dumps({"response": f"Nom d'utilisateur/Mot de passe invalide"}),
                status=404,
            )
    

    def signup(request, database): 
        request_form = request.form
        if "username" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: username not provided."}),
                status=400,
            )

        if "password" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: password not provided."}),
                status=400,
            )
        if "role" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: password not provided."}),
                status=400,
            )
        username = request_form['username']
        password = request_form['password']
        role = request_form['role']

        #TODO check if admin 
        collection = database["users"]

        isUserExisting = collection.count_documents({"username": username}) > 0
        print(isUserExisting)
        if isUserExisting : 
            return Response(
                response=json.dumps({"response": f"Nom d'utilisateur existant"}),
                status=404,
            )
        
        hashed_password = generate_password_hash(password, method='sha256') 

        user = {
            "username": username,
            "password": hashed_password,
            "role": role,
            "saveVerifiedImages": False,
            "moodleStructureInd": False,
        }
        collection.insert_one(user)

        return Response(
            response=json.dumps({"response": f'Utilisateur Créé'}),
            status=200
        )

    def update_save_verified_images(request, database): 
        request_form = request.form
        if "username" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: username not provided."}),
                status=400,
            )
        if "saveVerifiedImages" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: saveVerifiedImages not provided."}),
                status=400,
            )
        username = request_form['username']
        save_verified_images = bool(int(request_form['saveVerifiedImages']))

        collection = database["users"]

        user = { "$set": { 'saveVerifiedImages': save_verified_images } }
        
        collection.update_one({'username': username}, user)

        return Response(
            response=json.dumps({"response": f'Utilisateur mise-à-jour'}),
        )

    def update_moodle_structure_ind(request, database): 
        request_form = request.form
        if "username" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: username not provided."}),
                status=400,
            )
        if "moodleStructureInd" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: moodleStructureInd not provided."}),
                status=400,
            )
        username = request_form['username']
        moodle_structure_ind = bool(int(request_form['moodleStructureInd']))

        collection = database["users"]

        user = { "$set": { 'moodleStructureInd': moodle_structure_ind } }
        
        collection.update_one({'username': username}, user)

        return Response(
            response=json.dumps({"response": f'Utilisateur mise-à-jour'}),
        )

    def change_password(request, database): 
        request_form = request.form
        if "username" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: username not provided."}),
                status=400,
            )
        if "old_password" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: old_password not provided."}),
                status=400,
            )
        if "new_password" not in request_form:
            return Response(
                response=json.dumps({"response": f"Error: new_password not provided."}),
                status=400,
            )
        username = request_form['username']
        collection = database["users"]
        old_password = request_form['old_password']
        new_password = request_form['new_password']

        collection = database["users"]
        userDB = collection.find_one({"username": username})

        if not check_password_hash(userDB['password'], old_password) :

            return Response(
                response=json.dumps({"response": 'Le mot de passe entré est incorrect!'}),
                status=500
                )

        
        collection.update_one(
            {
                'username': username
            }, 
            { 
                "$set": { 'password': generate_password_hash(new_password, method='sha256')  }
            }
        )
        
        return Response(
                response=json.dumps({"response": 'Le mot de Passe a été modifié!'}),
                status=200
                )
        

        

