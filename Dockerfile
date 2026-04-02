FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Create uploads directory
RUN mkdir -p backend/uploads

# Expose port 7860 (required by Hugging Face Spaces)
EXPOSE 7860

# Start the app
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "120"]
