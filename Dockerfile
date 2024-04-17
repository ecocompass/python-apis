# Use an official Python runtime as a base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the Flask application code into the container
COPY app.py /app/
COPY consolidated_gtfs.json /app/
# Install Flask and other dependencies
RUN pip install --no-cache-dir flask flask_jwt_extended psycopg2-binary redis requests scipy

# Expose port 5000
EXPOSE 6969

# Command to run the Flask application
CMD ["python", "app.py"]
