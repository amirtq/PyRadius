FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure the entrypoint is executable
RUN chmod +x entrypoint.sh

# Expose RADIUS ports (UDP)
EXPOSE 1812/udp
EXPOSE 1813/udp

# Start the server
ENTRYPOINT ["./entrypoint.sh"]
