"""
Optional web API (FastAPI).

    uvicorn api:app --reload
    open http://127.0.0.1:8000/docs

NOTE: this demo has NO login. Before putting it on the internet, add authentication
and take the `role` from the logged-in user instead of the request body.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from gym_ai.database import init_db
from gym_ai.services import pdf_report, reports
from gym_ai.utils import GymError

app = FastAPI(title="Gym AI", description="AI gym management with LangChain + LangGraph + Claude")
init_db()
_graph = None   # built on first chat request, so the API starts even without an API key


class ChatRequest(BaseModel):
    message: str
    role: str = "member"
    thread_id: str = "web-session"


@app.get("/dashboard")
def dashboard():
    return reports.dashboard_stats()


@app.get("/reports/monthly")
def monthly_report(month: str | None = None):
    try:
        path = pdf_report.generate_monthly_pdf(month)
    except GymError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return FileResponse(path, media_type="application/pdf", filename=path.split("/")[-1])


@app.post("/chat")
def chat(request: ChatRequest):
    global _graph
    from gym_ai.agents.graph import ask, build_graph
    if _graph is None:
        _graph = build_graph()
    return {"reply": ask(_graph, request.message, request.role, request.thread_id)}
