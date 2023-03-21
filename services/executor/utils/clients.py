import os
import redis
import socketio
from pymongo import MongoClient


mongodb_user = os.getenv("MONGODB_USER", "adminuser")
mongodb_pass = os.getenv("MONGODB_PASSWORD", "example")
mongodb_host = "mongo" if os.getenv("ENVIRONNEMENT") == "production" else "localhost"
mongo_url = f"mongodb://{mongodb_user}:{mongodb_pass}@{mongodb_host}:27017/?retryWrites=true&w=majority"

redis_host = "redis" if os.getenv("ENVIRONNEMENT") == "production" else "localhost"
socketio_host = (
    "socketio" if os.getenv("ENVIRONNEMENT") == "production" else "localhost"
)


def mongo_client():
    return MongoClient(mongo_url)


def redis_client():
    return redis.Redis(host=redis_host, port=6379, db=0)


def socketio_client():
    sio = socketio.Client()
    sio.connect(f"http://{socketio_host}:7000")
    return sio
