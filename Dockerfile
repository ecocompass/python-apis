# Use an official Python runtime as a base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the Flask application code into the container
COPY app.py /app/

# Install Flask and other dependencies
RUN pip install --no-cache-dir flask flask_jwt_extended psycopg2-binary redis requests

# Expose port 5000
EXPOSE 6969

# Command to run the Flask application
CMD ["python", "app.py"]
