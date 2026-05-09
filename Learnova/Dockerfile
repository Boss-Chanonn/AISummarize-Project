# Use the official Python 3.10 slim image as the base
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements first (for Docker layer caching)
COPY requirements.txt .

# Install all Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all remaining project files into the container
COPY . .

# Expose port 8000 so it is accessible from outside the container
EXPOSE 8000

# Start the FastAPI app with uvicorn, listening on all interfaces
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
