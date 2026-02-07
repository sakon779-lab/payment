FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
<<<<<<< HEAD
EXPOSE 8000
=======
>>>>>>> e424b668ad8ffac8dd5b5d31c3191b1ad8f1986a
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]