from pymongo import MongoClient
import os

def get_mongo_client():
    mongo_uri = os.getenv('MONGO_URL')
    client = MongoClient(mongo_uri)
    return client

if __name__ == "__main__":
    client = get_mongo_client()