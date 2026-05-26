FROM python:3.13-slim

WORKDIR /app

ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

RUN pip install --no-cache-dir \
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
    elasticsearch[async]>=8.15.0 \
    kazoo>=3.0.0 \
    sqlalchemy>=2.0.0 \
    aiokafka>=0.12.0 \
    nacos-sdk-python>=3.2.0 \
    email-validator>=2.0.0
    

COPY common/src/common /app/common
COPY services/forum-service/src /app/src

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.forum_service.main:app", "--host", "0.0.0.0", "--port", "8006"]