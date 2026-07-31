from pymongo import MongoClient
from app.config import Config

class Database:
    """MongoDB Singleton Database Connection Manager."""
    _client = None
    _db = None

    @classmethod
    def get_db(cls):
        if cls._db is None:
            if not Config.MONGO_URI:
                Config.validate()
            cls._client = MongoClient(Config.MONGO_URI)
            cls._db = cls._client["loan_management"]
        return cls._db

    @classmethod
    def get_collection(cls, name: str):
        return cls.get_db()[name]

# Helper getters for database collections
def get_loan_collection():
    return Database.get_collection("loans")

def get_disbursement_collection():
    return Database.get_collection("loan_disbursements")

def get_interest_collection():
    return Database.get_collection("loan_interest_posting")

def get_emi_due_collection():
    return Database.get_collection("loan_emi_due")

def get_payment_collection():
    return Database.get_collection("loan_payments")

def get_penalty_collection():
    return Database.get_collection("loan_penalties")
