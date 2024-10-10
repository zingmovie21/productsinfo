from fastapi import FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
import logging
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# MongoDB connection details from environment variables
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
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

@app.get("/")
async def root():
    return {"message": "this is me adi"}

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
        transactions = await collection.find(query).skip(skip).limit(page_size).to_list(page_size)
        # Convert ObjectId to string for JSON serialization
        for transaction in transactions:
            transaction["_id"] = str(transaction["_id"])
        return transactions
    except Exception as e:
        logging.error(f"Error listing transactions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
        total_sales = total_sales[0]["total_sales"] if total_sales else 0
        total_items_sold = await collection.count_documents({"sold": True, "dateOfSale": {"$gte": start_date, "$lt": end_date}})
        total_items_not_sold = await collection.count_documents({"sold": False, "dateOfSale": {"$gte": start_date, "$lt": end_date}})
        
        return {
            "total_sales": total_sales,
            "total_items_sold": total_items_sold,
            "total_items_not_sold": total_items_not_sold
        }
    except Exception as e:
        logging.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
                "output": {
                    "count": {"$sum": 1}
                }
            }}
        ]

        bar_chart_data = await collection.aggregate(pipeline).to_list(None)
        return bar_chart_data
    except Exception as e:
        logging.error(f"Error generating bar chart data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
        logging.error(f"Error generating pie chart data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
        logging.error(f"Error retrieving combined data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
