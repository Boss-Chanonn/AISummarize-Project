"""
MongoDB Client & Collection Handles
====================================

Central database connection initialisation for the Learnova backend.  All
other modules import collection handles from here rather than constructing
their own ``AsyncIOMotorClient`` instances.

Lifecycle
---------
- The **client** is created at module load time using ``MONGO_URL`` from the
  environment (default ``mongodb://localhost:27017``).
- A connection-ping is performed during ``backend.main.startup_event`` to
  verify reachability.
- The **token blocklist TTL index** is also created at startup so that
  revoked-token documents are automatically expired.

Cross-references
----------------
- :mod:`backend.main` — Startup event pings MongoDB and creates TTL indexes.
- :mod:`backend.middleware.auth_middleware` — Reads ``token_blocklist_collection``
  and ``users_collection`` to validate authentication.
- :mod:`backend.routes.*` — Every route module imports the collections it needs
  from this module.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()


# ----------------------------- MongoDB Configuration -----------------------------
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "learnova_db")

# The single shared ``AsyncIOMotorClient`` instance for the entire application.
client = AsyncIOMotorClient(MONGO_URL)
db = client[DATABASE_NAME]

# Collections
# -----------
# Each attribute maps to a MongoDB collection.  Import these handles in route
# modules and service modules instead of creating separate connections.

# User accounts — stores profile data, roles, and authentication metadata.
users_collection = db["users"]

# Document processing history — records every summarisation / quiz-generation
# action for the per-user history view and the weekly email digest.
history_collection = db["history"]

# System activity log — populated by ``backend.main.log_activity`` middleware.
# Queried by sysadmin routes for the audit dashboard.
system_logs_collection = db["system_logs"]

# Revoked JWT tokens — populated on logout.  Has a TTL index on ``expireAt``
# (created in ``backend.main.startup_event``) so entries auto-delete after
# the token's natural expiry.
token_blocklist_collection = db["token_blocklist"]
