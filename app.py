from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.security.api_key import APIKeyHeader, APIKey
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# MongoDB connection details from environment variables
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = "test"
COLLECTION_NAME = "producttransactions"

# MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Model for Transactions
class Transaction(BaseModel):
    id: int
    title: str
    price: float
    description: str
    category: str
    image: str
    sold: bool
    dateOfSale: datetime

# API Key Authentication
API_KEY_NAME = "access_token"
API_KEY = os.getenv("API_KEY")  # Load API key from environment

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key_header: str = Depends(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

# Endpoint to check MongoDB connection and retrieve data
@app.get("/check-connection", dependencies=[Depends(get_api_key)])
async def check_connection():
    try:
        transactions = await collection.find().to_list(10)
        # Convert ObjectId to string
        for transaction in transactions:
            transaction["_id"] = str(transaction["_id"])
        return {"status": "Connected", "sample_data": transactions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/", response_class=HTMLResponse)
async def show_info():
    return """
    <html>
        <head>
            <title>Aditya Devarshi</title>
        </head>
        <body>
            <h1>Hello, I am Aditya Devarshi</h1>
            <p>You can find more about me at: 
                <a href="https://www.adityadevarshi.online/#/" target="_blank">
                    https://www.adityadevarshi.online
                </a>
            </p>
        </body>
    </html>
    """
# List Transactions API (GET)
@app.get("/transactions", response_model=List[Transaction], dependencies=[Depends(get_api_key)])
async def list_transactions(
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
):
    try:
        query = {}
        if search:
            query = {
                "$or": [
                    {"title": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}},
                    {"price": {"$eq": float(search)}}
                ]
            }
        skip = (page - 1) * page_size
        transactions = await collection.find(query).skip(skip).limit(page_size).to_list(page_size)
        # Convert ObjectId to string
        for transaction in transactions:
            transaction["_id"] = str(transaction["_id"])
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Statistics API (GET)
@app.get("/statistics", dependencies=[Depends(get_api_key)])
async def get_statistics(month: int, year: int):
    try:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        total_sales = await collection.aggregate([
            {"$match": {"sold": True, "dateOfSale": {"$gte": start_date, "$lt": end_date}}},
            {"$group": {"_id": None, "total_sales": {"$sum": "$price"}}}
        ]).to_list(None)
        total_sales = total_sales[0]["total_sales"] if total_sales else 0
        total_items_sold = await collection.count_documents({"sold": True, "dateOfSale": {"$gte": start_date, "$lt": end_date}})
        total_items_not_sold = await collection.count_documents({"sold": False, "dateOfSale": {"$gte": start_date, "$lt": end_date}})
        
        return {
            "total_sales": total_sales,
            "total_items_sold": total_items_sold,
            "total_items_not_sold": total_items_not_sold
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Bar Chart API (GET)
@app.get("/bar-chart", dependencies=[Depends(get_api_key)])
async def get_bar_chart(month: int, year: int):
    try:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        pipeline = [
            {"$match": {"sold": True, "dateOfSale": {"$gte": start_date, "$lt": end_date}}},
            {"$bucket": {
                "groupBy": "$price",
                "boundaries": [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, float('inf')],
                "default": "Other",
                "output": {
                    "count": {"$sum": 1}
                }
            }}
        ]
        
        bar_chart_data = await collection.aggregate(pipeline).to_list(None)
        return bar_chart_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Pie Chart API (GET)
@app.get("/pie-chart", dependencies=[Depends(get_api_key)])
async def get_pie_chart(month: int, year: int):
    try:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        pipeline = [
            {"$match": {"dateOfSale": {"$gte": start_date, "$lt": end_date}}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        
        pie_chart_data = await collection.aggregate(pipeline).to_list(None)
        return pie_chart_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/combined-data", dependencies=[Depends(get_api_key)])
async def get_combined_data(month: int, year: int):
    try:
        transactions = await list_transactions(page=1, page_size=10)
        statistics = await get_statistics(month, year)
        bar_chart = await get_bar_chart(month, year)
        pie_chart = await get_pie_chart(month, year)
        
        return {
            "transactions": transactions,
            "statistics": statistics,
            "bar_chart": bar_chart,
            "pie_chart": pie_chart
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
