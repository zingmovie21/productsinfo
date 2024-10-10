from fastapi import FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# MongoDB connection details from environment variables
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = "test"
COLLECTION_NAME = "producttransactions"

# MongoDB client and collection
client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

app = FastAPI()

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

# Utility function to handle MongoDB transactions
async def fetch_transactions(query={}, skip=0, limit=10):
    try:
        transactions = await collection.find(query).skip(skip).limit(limit).to_list(limit)
        for transaction in transactions:
            transaction["_id"] = str(transaction["_id"])  # Convert ObjectId to string
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")

# Root route
@app.get("/")
async def root():
    return {"message": "This is me, Adi"}

# Endpoint to check MongoDB connection and retrieve data
@app.get("/check-connection")
async def check_connection():
    try:
        transactions = await fetch_transactions(limit=10)
        return {"status": "Connected", "sample_data": transactions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# List Transactions API (GET)
@app.get("/transactions", response_model=List[Transaction])
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
        transactions = await fetch_transactions(query, skip=skip, limit=page_size)
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Statistics API (GET)
@app.get("/statistics")
async def get_statistics(month: int, year: int):
    try:
        start_date = datetime(year, month, 1)
        end_date = datetime(year + (month // 12), (month % 12) + 1, 1)
        
        total_sales = await collection.aggregate([
            {"$match": {"sold": True, "dateOfSale": {"$gte": start_date, "$lt": end_date}}},
            {"$group": {"_id": None, "total_sales": {"$sum": "$price"}}}
        ]).to_list(None)
        
        total_items_sold = await collection.count_documents({"sold": True, "dateOfSale": {"$gte": start_date, "$lt": end_date}})
        total_items_not_sold = await collection.count_documents({"sold": False, "dateOfSale": {"$gte": start_date, "$lt": end_date}})
        
        return {
            "total_sales": total_sales[0]["total_sales"] if total_sales else 0,
            "total_items_sold": total_items_sold,
            "total_items_not_sold": total_items_not_sold
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating statistics: {str(e)}")

# Bar Chart API (GET)
@app.get("/bar-chart")
async def get_bar_chart(month: int, year: int):
    try:
        start_date = datetime(year, month, 1)
        end_date = datetime(year + (month // 12), (month % 12) + 1, 1)
        
        pipeline = [
            {"$match": {"sold": True, "dateOfSale": {"$gte": start_date, "$lt": end_date}}},
            {"$bucket": {
                "groupBy": "$price",
                "boundaries": [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, float('inf')],
                "default": "Other",
                "output": {"count": {"$sum": 1}}
            }}
        ]
        
        bar_chart_data = await collection.aggregate(pipeline).to_list(None)
        return bar_chart_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating bar chart: {str(e)}")

# Pie Chart API (GET)
@app.get("/pie-chart")
async def get_pie_chart(month: int, year: int):
    try:
        start_date = datetime(year, month, 1)
        end_date = datetime(year + (month // 12), (month % 12) + 1, 1)
        
        pipeline = [
            {"$match": {"dateOfSale": {"$gte": start_date, "$lt": end_date}}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        
        pie_chart_data = await collection.aggregate(pipeline).to_list(None)
        return pie_chart_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating pie chart: {str(e)}")

# Combined Data API (GET)
@app.get("/combined-data")
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
        raise HTTPException(status_code=500, detail=f"Error fetching combined data: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
