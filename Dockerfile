FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir langgraph langchain-core langchain-mistralai langchain-openai langchain-anthropic python-dotenv pydantic pyyaml fastapi uvicorn httpx

COPY src/ ./src/
COPY tenants/ ./tenants/

EXPOSE 10000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "10000"]
