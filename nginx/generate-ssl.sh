#!/bin/bash
set -e

SSL_DIR="/etc/nginx/ssl"
CERT_FILE="${SSL_DIR}/server.crt"
KEY_FILE="${SSL_DIR}/server.key"

# SSL Configuration from environment variables (with defaults for backwards compatibility)
SSL_DOMAIN="${SSL_DOMAIN:-localhost}"
SSL_DAYS="${SSL_DAYS:-365}"
SSL_COUNTRY="${SSL_COUNTRY:-US}"
SSL_STATE="${SSL_STATE:-State}"
SSL_CITY="${SSL_CITY:-City}"
SSL_ORGANIZATION="${SSL_ORGANIZATION:-PyRadius}"

# Create SSL directory if it doesn't exist
mkdir -p "${SSL_DIR}"

# Check if certificates already exist
if [ -f "${CERT_FILE}" ] && [ -f "${KEY_FILE}" ]; then
    echo "SSL certificates already exist, skipping generation."
    echo "  Certificate: ${CERT_FILE}"
    echo "  Key: ${KEY_FILE}"
    
    # Verify the certificate is valid
    if openssl x509 -checkend 0 -noout -in "${CERT_FILE}" 2>/dev/null; then
        echo "Certificate is valid."
        exit 0
    else
        echo "WARNING: Certificate has expired or is invalid. Regenerating..."
    fi
fi

echo "Generating self-signed SSL certificate..."
echo "  Domain: ${SSL_DOMAIN}"
echo "  Validity: ${SSL_DAYS} days"
echo "  Organization: ${SSL_ORGANIZATION}"
echo "  Location: ${SSL_CITY}, ${SSL_STATE}, ${SSL_COUNTRY}"

# Generate self-signed certificate
openssl req -x509 -nodes -days "${SSL_DAYS}" -newkey rsa:2048 \
    -keyout "${KEY_FILE}" \
    -out "${CERT_FILE}" \
    -subj "/C=${SSL_COUNTRY}/ST=${SSL_STATE}/L=${SSL_CITY}/O=${SSL_ORGANIZATION}/OU=IT/CN=${SSL_DOMAIN}" \
    -addext "subjectAltName=DNS:${SSL_DOMAIN},DNS:localhost,IP:127.0.0.1"

# Set proper permissions
chmod 600 "${KEY_FILE}"
chmod 644 "${CERT_FILE}"

echo "SSL certificate generated successfully!"
echo "  Certificate: ${CERT_FILE}"
echo "  Key: ${KEY_FILE}"
