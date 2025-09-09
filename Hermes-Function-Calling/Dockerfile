FROM python:3.12-slim
ENV TOKENIZERS_PARALLELISM=true
RUN chmod 777 /tmp
WORKDIR /app
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "300"]
