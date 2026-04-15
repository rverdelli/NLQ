"""FastAPI application for the E-Commerce Data Chatbot."""

import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from models import ChatRequest, ChatResponse, QueryInfo, SchemaResponse
from database import get_schema_info, get_meta_layer
from claude_service import chat, chat_stream

app = FastAPI(title="DataChat — E-Commerce Analytics Assistant")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/schema")
def get_schema():
    tables = get_schema_info()
    return SchemaResponse(tables=tables)


@app.get("/api/suggestions")
def get_suggestions():
    return {
        "suggestions": [
            "What were the total sales by country last year?",
            "Show me the top 10 best-selling products",
            "How did revenue trend month over month in 2024?",
            "Which customer segment is most profitable?",
            "Compare marketing campaign ROI",
            "What are the most reviewed products?",
            "Show me order status distribution",
            "Which brands generate the most revenue?",
            "What is the average order value by payment method?",
            "Show me customer registrations over time",
        ]
    }


@app.get("/api/meta")
def get_meta():
    return get_meta_layer()


@app.post("/api/chat/stream")
def chat_stream_endpoint(req: ChatRequest):
    def generate():
        try:
            for event in chat_stream(req.message, req.history):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    try:
        result = chat(req.message, req.history)
        return ChatResponse(
            reply=result["reply"],
            chart=result.get("chart"),
            query_info=QueryInfo(**result["query_info"]) if result.get("query_info") else None,
            suggestions=result.get("suggestions", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_index():
    return FileResponse("static/index.html")
