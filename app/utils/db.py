from bson import ObjectId
from datetime import datetime
from pymongo import MongoClient
import os

# MongoDB connection
_mongo_client = None
_mongo_db = None

def get_mongo_client():
    """Get or create MongoDB client"""
    global _mongo_client
    if _mongo_client is None:
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        _mongo_client = MongoClient(mongo_uri)
    return _mongo_client

def get_mongo_db():
    """Get MongoDB database"""
    global _mongo_db
    if _mongo_db is None:
        client = get_mongo_client()
        db_name = os.getenv("MONGODB_DB_NAME", "telcenter_partner")
        _mongo_db = client[db_name]
    return _mongo_db

def serialize_mongo_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if doc is None:
        return None
    
    if isinstance(doc, list):
        return [serialize_mongo_doc(item) for item in doc]
    
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if key == '_id':
                result['id'] = str(value)  # Convert ObjectId to string
            elif isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = serialize_mongo_doc(value)
            elif isinstance(value, list):
                result[key] = serialize_mongo_doc(value)
            else:
                result[key] = value
        return result
    
    return doc

def str_to_objectid(id_str):
    """Convert string ID to ObjectId"""
    try:
        return ObjectId(id_str)
    except:
        return None
