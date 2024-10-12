from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import motor.motor_asyncio
from bson import ObjectId
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get environment variables
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# MongoDB connection
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

class Transaction(BaseModel):
    id: str
    title: str
    description: str
    price: float
    dateOfSale: datetime
    category: str
    sold: bool
    image: Optional[str] = None

class Pagination(BaseModel):
    page: int = 1
    per_page: int = 10

@app.get("/transactions", response_model=List[Transaction])
async def list_transactions(search: Optional[str] = None, page: int = 1, per_page: int = 10):
    query = {}
    if search:
        query = {
            "$or": [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"price": {"$regex": search, "$options": "i"}}
            ]
        }
    skip = (page - 1) * per_page
    cursor = collection.find(query).skip(skip).limit(per_page)
    transactions = await cursor.to_list(length=per_page)
    for transaction in transactions:
        transaction['id'] = str(transaction['_id'])
        transaction['image'] = transaction.get('image', '')
        del transaction['_id']
    return transactions

@app.get("/statistics")
async def get_statistics(month: str):
    month_number = datetime.strptime(month, "%B").month
    pipeline = [
        {"$match": {"$expr": {"$eq": [{"$month": "$dateOfSale"}, month_number]}}},
        {"$group": {
            "_id": None,
            "total_sale_amount": {"$sum": "$price"},
            "total_sold_items": {"$sum": {"$cond": ["$sold", 1, 0]}},
            "total_not_sold_items": {"$sum": {"$cond": ["$sold", 0, 1]}}
        }}
    ]
    result = await collection.aggregate(pipeline).to_list(length=1)
    if result:
        return result[0]
    return {"total_sale_amount": 0, "total_sold_items": 0, "total_not_sold_items": 0}

@app.get("/bar_chart")
async def get_bar_chart(month: str):
    month_number = datetime.strptime(month, "%B").month
    pipeline = [
        {"$match": {"$expr": {"$eq": [{"$month": "$dateOfSale"}, month_number]}}},
        {"$bucket": {
            "groupBy": "$price",
            "boundaries": [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, float("inf")],
            "default": "901-above",
            "output": {"count": {"$sum": 1}}
        }}
    ]
    result = await collection.aggregate(pipeline).to_list(length=10)
    return result

@app.get("/pie_chart")
async def get_pie_chart(month: str):
    month_number = datetime.strptime(month, "%B").month
    pipeline = [
        {"$match": {"$expr": {"$eq": [{"$month": "$dateOfSale"}, month_number]}}},
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1}
        }}
    ]
    result = await collection.aggregate(pipeline).to_list(length=100)
    return result

@app.get("/combined")
async def get_combined(month: str):
    transactions = await list_transactions(page=1, per_page=10)
    statistics = await get_statistics(month)
    bar_chart = await get_bar_chart(month)
    pie_chart = await get_pie_chart(month)
    return {
        "transactions": transactions,
        "statistics": statistics,
        "bar_chart": bar_chart,
        "pie_chart": pie_chart
    }
