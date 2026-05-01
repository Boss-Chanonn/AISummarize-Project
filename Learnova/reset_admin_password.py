import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "learnova_db")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

NEW_PASSWORD = "Admin@12345"
ADMIN_EMAIL  = "admin@learnova.com"

async def reset():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DATABASE_NAME]

    user = await db["users"].find_one({"email": ADMIN_EMAIL})
    if not user:
        print(f"[error] No user found with email: {ADMIN_EMAIL}")
        client.close()
        return

    new_hash = pwd_context.hash(NEW_PASSWORD)
    await db["users"].update_one(
        {"email": ADMIN_EMAIL},
        {"$set": {"password": new_hash, "role": "admin"}}
    )
    print(f"[done]  Password reset successfully")
    print(f"        Email   : {ADMIN_EMAIL}")
    print(f"        Password: {NEW_PASSWORD}")
    print(f"        Role    : admin")
    client.close()

asyncio.run(reset())
