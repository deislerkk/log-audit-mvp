FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY audit_agent.py /app/audit_agent.py
COPY rules.yml /app/rules.yml
ENV PYTHONUNBUFFERED=1
CMD ["python", "audit_agent.py"]
