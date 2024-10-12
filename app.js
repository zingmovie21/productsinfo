
const express = require('express');
const mongoose = require('mongoose');
const dotenv = require('dotenv');
const helmet = require('helmet');
const path = require('path');

// Load environment variables from .env file
dotenv.config();

const app = express();
app.use(helmet());
const PORT = process.env.PORT || 3000;
const MONGODB_URL = process.env.MONGODB_URL;
const DATABASE_NAME = process.env.DATABASE_NAME;
const COLLECTION_NAME = process.env.COLLECTION_NAME;

// MongoDB connection
mongoose.connect(MONGODB_URL, { useNewUrlParser: true, useUnifiedTopology: true });
const db = mongoose.connection;
db.on('error', console.error.bind(console, 'connection error:'));
db.once('open', () => {
    console.log('Connected to MongoDB');
});

const transactionSchema = new mongoose.Schema({
    title: String,
    description: String,
    price: Number,
    dateOfSale: Date,
    category: String,
    sold: Boolean,
    image: String
});

const Transaction = mongoose.model(COLLECTION_NAME, transactionSchema, COLLECTION_NAME);

app.use('/static', express.static(path.join(__dirname, 'static')));

app.get('/transactions', async (req, res) => {
    const { search, page = 1, per_page = 10 } = req.query;
    const query = search ? {
        $or: [
            { title: { $regex: search, $options: 'i' } },
            { description: { $regex: search, $options: 'i' } },
            { price: { $regex: search, $options: 'i' } }
        ]
    } : {};
    const skip = (page - 1) * per_page;
    const transactions = await Transaction.find(query).skip(skip).limit(parseInt(per_page));
    res.json(transactions);
});

app.get('/statistics', async (req, res) => {
    const { month } = req.query;
    const monthNumber = new Date(Date.parse(month + " 1, 2021")).getMonth() + 1;
    const pipeline = [
        { $match: { $expr: { $eq: [{ $month: "$dateOfSale" }, monthNumber] } } },
        {
            $group: {
                _id: null,
                total_sale_amount: { $sum: "$price" },
                total_sold_items: { $sum: { $cond: ["$sold", 1, 0] } },
                total_not_sold_items: { $sum: { $cond: ["$sold", 0, 1] } }
            }
        }
    ];
    const result = await Transaction.aggregate(pipeline);
    res.json(result[0] || { total_sale_amount: 0, total_sold_items: 0, total_not_sold_items: 0 });
});

app.get('/bar_chart', async (req, res) => {
    const { month } = req.query;
    const monthNumber = new Date(Date.parse(month + " 1, 2021")).getMonth() + 1;
    const pipeline = [
        { $match: { $expr: { $eq: [{ $month: "$dateOfSale" }, monthNumber] } } },
        {
            $bucket: {
                groupBy: "$price",
                boundaries: [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, Infinity],
                default: "901-above",
                output: { count: { $sum: 1 } }
            }
        }
    ];
    const result = await Transaction.aggregate(pipeline);
    res.json(result);
});

app.get('/pie_chart', async (req, res) => {
    const { month } = req.query;
    const monthNumber = new Date(Date.parse(month + " 1, 2021")).getMonth() + 1;
    const pipeline = [
        { $match: { $expr: { $eq: [{ $month: "$dateOfSale" }, monthNumber] } } },
        {
            $group: {
                _id: "$category",
                count: { $sum: 1 }
            }
        }
    ];
    const result = await Transaction.aggregate(pipeline);
    res.json(result);
});

app.get('/combined', async (req, res) => {
    const { month } = req.query;
    const transactions = await Transaction.find().limit(10);
    const statistics = await getStatistics(month);
    const bar_chart = await getBarChart(month);
    const pie_chart = await getPieChart(month);
    res.json({
        transactions,
        statistics,
        bar_chart,
        pie_chart
    });
});

async function getStatistics(month) {
    const monthNumber = new Date(Date.parse(month + " 1, 2021")).getMonth() + 1;
    const pipeline = [
        { $match: { $expr: { $eq: [{ $month: "$dateOfSale" }, monthNumber] } } },
        {
            $group: {
                _id: null,
                total_sale_amount: { $sum: "$price" },
                total_sold_items: { $sum: { $cond: ["$sold", 1, 0] } },
                total_not_sold_items: { $sum: { $cond: ["$sold", 0, 1] } }
            }
        }
    ];
    const result = await Transaction.aggregate(pipeline);
    return result[0] || { total_sale_amount: 0, total_sold_items: 0, total_not_sold_items: 0 };
}

async function getBarChart(month) {
    const monthNumber = new Date(Date.parse(month + " 1, 2021")).getMonth() + 1;
    const pipeline = [
        { $match: { $expr: { $eq: [{ $month: "$dateOfSale" }, monthNumber] } } },
        {
            $bucket: {
                groupBy: "$price",
                boundaries: [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, Infinity],
                default: "901-above",
                output: { count: { $sum: 1 } }
            }
        }
    ];
    const result = await Transaction.aggregate(pipeline);
    return result;
}

async function getPieChart(month) {
    const monthNumber = new Date(Date.parse(month + " 1, 2021")).getMonth() + 1;
    const pipeline = [
        { $match: { $expr: { $eq: [{ $month: "$dateOfSale" }, monthNumber] } } },
        {
            $group: {
                _id: "$category",
                count: { $sum: 1 }
            }
        }
    ];
    const result = await Transaction.aggregate(pipeline);
    return result;
}

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
