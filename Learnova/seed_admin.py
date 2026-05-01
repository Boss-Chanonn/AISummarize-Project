"""
seed_admin.py — สร้าง default admin user ใน MongoDB

Usage:
    python seed_admin.py

Default credentials:
    Email   : admin@learnova.com
    Password: Admin@12345
    Role    : admin
"""

import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URL     = os.getenv("MONGO_URL",     "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "learnova_db")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ADMIN_USER = {
    "name":      "Admin",
    "email":     "admin@learnova.com",
    "password":  "Admin@12345",   # plain — will be hashed below
    "dob":       "1990-01-01",
    "phone":     "",
    "role":      "admin",
    "tier":      "free",
}

async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db     = client[DATABASE_NAME]
    users  = db["users"]

    existing = await users.find_one({"email": ADMIN_USER["email"]})
    if existing:
        print(f"[skip]  Admin user already exists: {ADMIN_USER['email']}")
        client.close()
        return

    hashed = pwd_context.hash(ADMIN_USER["password"])
    await users.insert_one({
        "name":      ADMIN_USER["name"],
        "email":     ADMIN_USER["email"],
        "password":  hashed,
        "dob":       ADMIN_USER["dob"],
        "phone":     ADMIN_USER["phone"],
        "role":      ADMIN_USER["role"],
        "tier":      ADMIN_USER["tier"],
        "createdAt": datetime.utcnow(),
    })

    print(f"[done]  Admin user created successfully")
    print(f"        Email   : {ADMIN_USER['email']}")
    print(f"        Password: {ADMIN_USER['password']}")
    print(f"        Role    : {ADMIN_USER['role']}")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
