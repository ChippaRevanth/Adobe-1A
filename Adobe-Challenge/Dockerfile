# Dockerfile
# Use a Python 3.10 slim image for a smaller footprint
FROM --platform=linux/amd64 python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
# This helps with Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the processing script
COPY process_pdfs.py .

# Command to run the script
CMD ["python", "process_pdfs.py"]