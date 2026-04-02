FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p backend/uploads

EXPOSE 7860

CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "120"]
