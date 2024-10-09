from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# MongoDB connection using environment variable
mongo_uri = os.environ.get('MONGO_URI')
client = MongoClient(mongo_uri)
db = client['test']  # Replace 'test' with your actual database name
transactions_collection = db['producttransactions']

# API to list all transactions with search and pagination
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    skip = (page - 1) * per_page

    query = {}
    if search:
        query = {"$or": [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"price": {"$regex": search, "$options": "i"}}
        ]}

    transactions = transactions_collection.find(query).skip(skip).limit(per_page)
    result = [{"id": t.get('id', ''), "title": t.get('title', ''), 
               "price": t.get('price', 0), "description": t.get('description', ''), 
               "category": t.get('category', ''), "image": t.get('image', ''), 
               "sold": t.get('sold', False), "dateOfSale": t.get('dateOfSale', 'N/A')}
              for t in list(transactions)]
    return jsonify(result)

# API for statistics (Total sales, sold/not sold items)
@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    start_date = datetime.strptime(f"{month}-01", "%Y-%m-%d")
    end_date = datetime.strptime(f"{month}-01", "%Y-%m-%d").replace(month=start_date.month + 1)

    total_sales = transactions_collection.aggregate([
        {"$match": {"dateOfSale": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": None, "total_sales": {"$sum": "$price"}}}
    ])

    total_sold = transactions_collection.count_documents({"dateOfSale": {"$gte": start_date, "$lt": end_date}, "sold": True})
    not_sold = transactions_collection.count_documents({"dateOfSale": {"$gte": start_date, "$lt": end_date}, "sold": False})

    return jsonify({
        "total_sales": list(total_sales)[0]['total_sales'] if total_sales else 0,
        "total_sold": total_sold,
        "not_sold": not_sold
    })

# API for bar chart (Price range distribution)
@app.route('/api/bar-chart', methods=['GET'])
def get_bar_chart():
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    start_date = datetime.strptime(f"{month}-01", "%Y-%m-%d")
    end_date = datetime.strptime(f"{month}-01", "%Y-%m-%d").replace(month=start_date.month + 1)

    price_ranges = [
        {"range": "0-100", "min": 0, "max": 100},
        {"range": "101-200", "min": 101, "max": 200},
        {"range": "201-300", "min": 201, "max": 300},
        {"range": "301-400", "min": 301, "max": 400},
        {"range": "401-500", "min": 401, "max": 500},
        {"range": "501-600", "min": 501, "max": 600},
        {"range": "601-700", "min": 601, "max": 700},
        {"range": "701-800", "min": 701, "max": 800},
        {"range": "801-900", "min": 801, "max": 900},
        {"range": "901-above", "min": 901, "max": float('inf')}
    ]

    result = []
    for pr in price_ranges:
        count = transactions_collection.count_documents({
            "dateOfSale": {"$gte": start_date, "$lt": end_date},
            "price": {"$gte": pr["min"], "$lt": pr["max"]}
        })
        result.append({"range": pr["range"], "count": count})

    return jsonify(result)

# API for pie chart (Unique categories)
@app.route('/api/pie-chart', methods=['GET'])
def get_pie_chart():
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    start_date = datetime.strptime(f"{month}-01", "%Y-%m-%d")
    end_date = datetime.strptime(f"{month}-01", "%Y-%m-%d").replace(month=start_date.month + 1)

    categories = transactions_collection.aggregate([
        {"$match": {"dateOfSale": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ])

    result = [{"category": c['_id'], "count": c['count']} for c in categories]
    return jsonify(result)

# API to fetch combined data from all the above APIs
@app.route('/api/combined-data', methods=['GET'])
def get_combined_data():
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))

    transactions = get_transactions().get_json()
    statistics = get_statistics().get_json()
    bar_chart = get_bar_chart().get_json()
    pie_chart = get_pie_chart().get_json()

    return jsonify({
        "transactions": transactions,
        "statistics": statistics,
        "bar_chart": bar_chart,
        "pie_chart": pie_chart
    })

if __name__ == '__main__':
    app.run(debug=True)
