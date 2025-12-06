# Stage 1: Build Frontend
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Backend
FROM python:3.13-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend project files
COPY backend/ .

# Copy entrypoint script
COPY entrypoint.sh .

# Copy Frontend Build
COPY --from=frontend /frontend/dist /app/frontend_dist

# Ensure the entrypoint is executable
RUN chmod +x entrypoint.sh

# Expose RADIUS ports (UDP) and Web port
EXPOSE 8000
EXPOSE 1812/udp
EXPOSE 1813/udp

# Start the server
ENTRYPOINT ["./entrypoint.sh"]
