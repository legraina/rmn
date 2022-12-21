import gridfs
from pymongo import MongoClient
from bson.objectid import ObjectId
from pathlib import Path

print("Setting up MongoClient...")
mongo_client = MongoClient('mongodb+srv://adminuser:adminuser1234@cluster0.qf13kcj.mongodb.net/?retryWrites=true&w=majority')

db = mongo_client["RMN"]
collection = db["eval_jobs"]

fs = gridfs.GridFS(db)

preview_file_byte = fs.find({"_id": ObjectId('633781482bc13624d668bea9')}).next().read()

OUTPUT_FOLDER = Path(__file__).resolve().parent.joinpath("output")

with open("preview.pdf", "wb") as f_out:
        f_out.write(preview_file_byte)
print("preview file created")