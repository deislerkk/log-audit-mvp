FROM python:3.11-slim
WORKDIR /app
COPY generator.py /app/generator.py
RUN pip install --no-cache-dir python-dateutil
CMD ["python", "generator.py"]
