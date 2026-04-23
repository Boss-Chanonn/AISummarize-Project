import os
from fastapi import FastAPI 
from mangum import Mangum 
from motor.motor_asyncio import AsyncIOMotorClient 

app = FastAPI() 

#Database Connection (defined outside of the handler for performance)
#Use environment variables that you set in Lambda Console 
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.get_database("AI_Summarize_Project")

#GET request = HTTP method in order to read or receive data from (loading website page)
#Web application route  with an get request (main open page)
@app.get("/") 
#Asynchronous function root - (name of function)
async def root(): 
    return {
        "status": "online",
        "message":"AI Summarize API is working and running!",
        "database": "Connected" if MONGODB_URI else "Missing URI"
    }

@app.get("/test-database-connection")
async def test_database_connection(): 
#simple check to see if their is an connection with MongoDB database 
    collections = await db.list_collection_names()#request for all database collections (list of tables) 
    return{"collections":collections}

handler = Mangum(app, lifespan="off")
#Handle FastAPI application (app) and also connect to database
