import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URL     = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "learnova_db")

async def check():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DATABASE_NAME]

    admin = await db["users"].find_one({"email": "admin@learnova.com"})
    if admin:
        print("[OK]   Admin user exists")
        print(f"       email : {admin.get('email')}")
        print(f"       role  : {admin.get('role')}")
        print(f"       tier  : {admin.get('tier')}")
    else:
        print("[MISS] admin@learnova.com not found in DB")

    total = await db["users"].count_documents({})
    print(f"[INFO] Total users in DB: {total}")
    client.close()

asyncio.run(check())
