ARG API_BASE_IMAGE=python:3.12-slim
FROM ${API_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG PIP_INDEX_URL=https://mirrors.tencent.com/pypi/simple
ARG PIP_TRUSTED_HOST=mirrors.tencent.com

ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}
ENV PIP_DEFAULT_TIMEOUT=120
ENV PIP_RETRIES=10
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /service

COPY apps/api/pyproject.toml ./pyproject.toml
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir . "pytest>=8.0.0" "httpx>=0.27.0"

COPY apps/api/app ./app
COPY apps/api/tests ./tests

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

