FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE NOTICE ACKNOWLEDGMENTS.md ./
COPY src ./src
COPY config ./config
COPY corpus ./corpus
COPY schemas ./schemas

RUN pip install --no-cache-dir .

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=3)"

CMD ["uvicorn", "docent.app:app", "--host", "0.0.0.0", "--port", "7860"]
