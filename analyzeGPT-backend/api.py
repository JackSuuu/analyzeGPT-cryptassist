import os
import json
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
from functools import partial
import asyncio

# Import your custom modules
from file_parsing import process_pdf, process_csv
from utils import make_output

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

async def get_btc_data_and_summary():
    """Shared function for BTC data updates"""
    loop = asyncio.get_event_loop()
    
    # Run synchronous function in thread pool
    await loop.run_in_executor(None, get_btc_graph_csvb)
    
    # Read generated CSV data
    df = pd.read_csv("binance_data.csv")
    
    # Create analysis prompt
    data_sample = df.tail(6).to_string()
    prompt = f"""Analyze this Bitcoin market data and create a concise summary highlighting:
    - Price trends
    - Volume changes
    - Key support/resistance levels
    - Notable patterns\n\n{data_sample}"""
    
    # Generate summary using OpenAI
    summary = await loop.run_in_executor(
        None, 
        partial(make_output, query=prompt, use_groq=False)
    )
    
    # Save to summaries.json with proper list handling
    summary_entry = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "data_source": "binance_data.csv",
        "summary": summary
    }
    
    summary_path = Path("docs/summaries.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if summary_path.exists():
            with open(summary_path, "r") as f:
                existing = json.load(f)
                
            # Ensure we're always working with a list
            if isinstance(existing, dict):
                existing = [existing]  # Convert single dict to list
            elif not isinstance(existing, list):
                existing = []
        else:
            existing = []
    except json.JSONDecodeError:
        existing = []
    
    existing.append(summary_entry)
    
    with open(summary_path, "w") as f:
        json.dump(existing, f, indent=2)
    
    return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background task when app starts
    asyncio.create_task(periodic_btc_update())
    yield

async def periodic_btc_update():
    """Periodically update BTC data and generate summary"""
    while True:
        try:
            await get_btc_data_and_summary()
            print("Successfully updated BTC data and summary")
        except Exception as e:
            print(f"Periodic update failed: {str(e)}")
        
        # Wait 30 minutes between runs
        await asyncio.sleep(1800)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/update-btc-data")
async def manual_btc_update():
    """Manual trigger for BTC data update"""
    try:
        success = await get_btc_data_and_summary()
        if success:
            return {
                "status": "success",
                "message": "BTC data and summary updated",
                "timestamp": pd.Timestamp.now().isoformat()
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Manual update failed: {str(e)}"
        )

# Core API Endpoints
class PDFResponse(BaseModel):
    summary: str

class QueryRequest(BaseModel):
    query: str
    use_groq: bool = True
    mode: str = "data"

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
        response = make_output(request.query, request.use_groq, request.mode) # mode is either "data" or "knowledge"
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)