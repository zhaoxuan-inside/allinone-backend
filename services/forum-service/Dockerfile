FROM python:3.13-slim

WORKDIR /app

COPY common/src /app/common/src

RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    fastapi>=0.115.0 \
    uvicorn[standard]>=0.32.0 \
    pydantic>=2.10.0 \
    pydantic-settings>=2.6.0 \
    redis>=5.2.0 \
    asyncpg>=0.30.0 \
    python-jose[cryptography]>=3.3.0 \
    passlib[bcrypt]>=1.7.4 \
    python-multipart>=0.0.17 \
    httpx>=0.27.2 \
    motor>=3.6.0 \
    elasticsearch[async]>=8.15.0

COPY services/forum-service/src /app/src

CMD ["uvicorn", "src.forum_service.main:app", "--host", "0.0.0.0", "--port", "8006"]