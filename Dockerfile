# Stage 1: Build Frontend
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
# Create backend directory for vite output (vite.config.js outputs to ../backend/frontend_dist)
RUN mkdir -p /backend/frontend_dist && npm run build

# Stage 2: Backend
FROM python:3.13-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Nginx, OpenSSL, and other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    openssl \
    && rm -rf /var/lib/apt/lists/* \
    && rm /etc/nginx/sites-enabled/default

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend project files
COPY backend/ .

# Copy entrypoint script
COPY entrypoint.sh .

# Copy Nginx configuration and SSL generation script
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx/generate-ssl.sh /usr/local/bin/generate-ssl.sh
RUN chmod +x /usr/local/bin/generate-ssl.sh

# Copy Frontend Build (vite outputs to /backend/frontend_dist based on vite.config.js)
COPY --from=frontend /backend/frontend_dist /app/frontend_dist

# Ensure the entrypoint is executable
RUN chmod +x entrypoint.sh

# Expose HTTP, HTTPS, and RADIUS ports
EXPOSE 80
EXPOSE 443
EXPOSE 1812/udp
EXPOSE 1813/udp

# Start the server
ENTRYPOINT ["./entrypoint.sh"]
