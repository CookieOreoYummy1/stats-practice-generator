from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from .llm_client import GenerationError, LLMClient
from .models import ProblemBatchResponse, ProblemPublic, ProblemRequest
from .prompts import TOPIC_TAXONOMY
from .store import ProblemStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    client = LLMClient()
    try:
        await run_in_threadpool(client.verify_credentials)
        app.state.llm_client = client
        app.state.store = ProblemStore()
        yield
    finally:
        await run_in_threadpool(client.close)


app = FastAPI(title="Stats Practice Problem Generator", lifespan=lifespan)


@app.get("/api/topics")
def topics() -> dict:
    return {"topics": [{"id": topic.value, **details} for topic, details in TOPIC_TAXONOMY.items()]}


@app.post("/api/generate", response_model=ProblemBatchResponse)
def generate(payload: ProblemRequest, request: Request) -> ProblemBatchResponse:
    try:
        problems = request.app.state.llm_client.generate_problems(payload)
    except GenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    request.app.state.store.add_many(problems)
    return ProblemBatchResponse(
        problems=[ProblemPublic.model_validate(problem.model_dump()) for problem in problems]
    )
