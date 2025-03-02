import os
import json
import base64
import asyncio
import websockets
import shutil
import requests
import pandas as pd
from fastapi import FastAPI, WebSocket, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
from dotenv import load_dotenv
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from pydantic import BaseModel
import uvicorn

# Import your custom modules
from file_parsing import process_pdf, process_csv
from utils import make_output, modify_output


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core API Endpoints
class PDFResponse(BaseModel):
    summary: str

class QueryRequest(BaseModel):
    query: str
    use_groq: bool = True

@app.post("/api/upload_pdf/", response_model=PDFResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=422, detail="Only PDF files allowed")
    
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:  # 100MB
        raise HTTPException(status_code=422, detail="File too large")
    
    await file.seek(0)
    try:
        file_path = Path("uploads") / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        summary = process_pdf(str(file_path))
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Processing failed: {str(e)}")

def importCryptoData():
    cryptoData = File()
    upload_csv()

@app.post("/api/upload_csv/", response_model=PDFResponse)
async def upload_csv(file: UploadFile = File(...)):
    if file.content_type != "text/csv":
        raise HTTPException(status_code=422, detail="CSV files only")
    
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="File exceeds 100MB")
    
    await file.seek(0)
    try:
        file_path = Path("uploads") / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        summary = process_csv(str(file_path))
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV error: {str(e)}")

@app.post("/api/generate_output/")
async def generate_output(request: QueryRequest):
    try:
        response = make_output(request.query, request.use_groq)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/summary", response_class=JSONResponse)
async def get_summary():
    summary_path = Path("docs/summaries.json")
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="Summary file not found")
    
    try:
        with open(summary_path, "r") as file:
            summary_data = json.load(file)
        return summary_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading summary file: {str(e)}")

# Data Generation
def get_btc_graph_csvb():
    """Generate BTC market data"""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "1h",
        "limit": 100
    }
    
    try:
        data = requests.get(url, params=params).json()
        df = pd.DataFrame(data, columns=[
            "Timestamp", "Open", "High", "Low", "Close", "Volume",
            "CloseTime", "QuoteAssetVolume", "Trades", "TakerBuyBase", 
            "TakerBuyQuote", "Ignore"
        ])
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit='ms')
        df.to_csv("binance_data.csv", index=False)
    except Exception as e:
        print(f"BTC data error: {str(e)}")