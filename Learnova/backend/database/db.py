from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()


# ----------------------------- MongoDB Configuration -----------------------------
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "learnova_db")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DATABASE_NAME]

# Collections
users_collection           = db["users"]
history_collection         = db["history"]
system_logs_collection     = db["system_logs"]
token_blocklist_collection = db["token_blocklist"]
