FROM python:3.12-slim

WORKDIR /app

# Non-root user for principle of least privilege
RUN useradd -m -u 1000 appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# --no-access-log: prevents request URLs (which could contain UUIDs) from
# appearing in container stdout. PHI access is tracked via AuditLogger instead.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
