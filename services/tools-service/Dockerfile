FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml poetry.lock ./
COPY ../../common /common

RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi

COPY . .

CMD ["uvicorn", "src.tools_service.main:app", "--host", "0.0.0.0", "--port", "8003"]