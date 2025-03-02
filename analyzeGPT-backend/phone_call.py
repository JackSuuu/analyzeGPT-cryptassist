import os
import json
import base64
import asyncio
import websockets
import feedparser
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
from dotenv import load_dotenv

from datetime import datetime, timedelta
import pandas as pd

def fetch_crypto_news(coin="Bitcoin"):
    """Fetch latest crypto news from Google News RSS"""
    try:
        # Fetch from Google News RSS
        news_url = f"https://news.google.com/rss/search?q={coin}&tbs=qdr:h"
        news_feed = feedparser.parse(news_url)
        
        # Process recent news (last 24 hours)
        recent_news = []
        for entry in news_feed.entries[:5]:  # Get top 5 news items
            news_item = {
                'title': entry.title,
                'link': entry.link,
                'published': entry.published,
                'source': entry.source.title if hasattr(entry, 'source') else "Unknown Source"
            }
            recent_news.append(news_item)
            
        return recent_news
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

load_dotenv()

# Load CSV data with proper column handling
CSV_PATH = "./binance_data.csv"
try:
    # Load CSV with specific column names
    df = pd.read_csv(CSV_PATH, parse_dates=['Timestamp'])
    print(f"Loaded CSV columns: {df.columns.tolist()}")
    
    # Process the data for analysis
    df = df.sort_values('Timestamp')
    
    # Get latest market data
    latest_data = df.iloc[-1]
    last_24h = df.tail(24)  # Last 24 hours of data
    
    # Calculate key metrics
    price_change_24h = ((latest_data['Close'] - last_24h.iloc[0]['Close']) / last_24h.iloc[0]['Close'] * 100)
    volume_24h = last_24h['Volume'].sum()
    trades_24h = last_24h['Trades'].sum()
    
    # Fetch latest news with better error handling
    try:
        latest_news = fetch_crypto_news()
        if latest
