#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "Configuring HTTPS on Gemini Chatbot VM"
echo "=========================================="

# 1. Remove old iptables PREROUTING port 80 redirect
echo "[1/7] Removing legacy iptables redirect..."
sudo iptables -t nat -D PREROUTING -p tcp --dport 80 -j REDIRECT --to-ports 5000 2>/dev/null || true

# 2. Update systemd service to run Flask on internal port 5001
echo "[2/7] Updating gemini-chatbot.service for internal port 5001..."
cat << 'EOF' | sudo tee /etc/systemd/system/gemini-chatbot.service
[Unit]
Description=Gemini Chatbot Web Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/gemini-chatbot
Environment="PORT=5001"
EnvironmentFile=/opt/gemini-chatbot/.env
ExecStart=/opt/gemini-chatbot/venv/bin/python /opt/gemini-chatbot/server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl restart gemini-chatbot.service

# Verify Flask is listening on 5001
sleep 3
if sudo ss -tlpn | grep -q ":5001"; then
    echo "-> Flask is successfully running on port 5001"
else
    echo "-> WARNING: Flask not detected on port 5001, checking status..."
    sudo systemctl status gemini-chatbot.service --no-pager || true
fi

# 3. Install Nginx and Certbot
echo "[3/7] Installing Nginx and Certbot..."
sudo DEBIAN_FRONTEND=noninteractive apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx certbot python3-certbot-nginx

# 4. Create self-signed fallback certificate
echo "[4/7] Generating high-grade SSL certificate with SAN..."
sudo mkdir -p /etc/ssl/chatbot
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/chatbot/selfsigned.key \
  -out /etc/ssl/chatbot/selfsigned.crt \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=GeminiChatbot/CN=34.45.106.67" \
  -addext "subjectAltName=IP:34.45.106.67,DNS:34.45.106.67.sslip.io,DNS:34-45-106-67.sslip.io"

# 5. Create webroot for Let's Encrypt validation
sudo mkdir -p /var/www/html/.well-known/acme-challenge
sudo chown -R www-data:www-data /var/www/html

# 6. Configure Nginx with initial SSL
echo "[5/7] Configuring Nginx reverse proxy..."
cat << 'EOF' | sudo tee /etc/nginx/sites-available/gemini-chatbot
# HTTP: ACME Challenge & Redirect to HTTPS
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS: Port 443 & Port 5000
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    listen 5000 ssl;
    listen [::]:5000 ssl;
    server_name _;

    ssl_certificate /etc/ssl/chatbot/selfsigned.crt;
    ssl_certificate_key /etc/ssl/chatbot/selfsigned.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE Streaming headers
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding on;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
EOF

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/gemini-chatbot /etc/nginx/sites-enabled/gemini-chatbot
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# 7. Request Let's Encrypt Certificate
echo "[6/7] Requesting Let's Encrypt CA certificate for sslip.io..."
set +e
sudo certbot certonly --webroot -w /var/www/html \
  -d 34-45-106-67.sslip.io \
  -d 34.45.106.67.sslip.io \
  --non-interactive --agree-tos --email songpa10@iceu.kr
CERTBOT_STATUS=$?
set -e

if [ $CERTBOT_STATUS -eq 0 ] && [ -f "/etc/letsencrypt/live/34-45-106-67.sslip.io/fullchain.pem" ]; then
    echo "-> Let's Encrypt certificate obtained successfully!"
    sudo sed -i 's|/etc/ssl/chatbot/selfsigned.crt|/etc/letsencrypt/live/34-45-106-67.sslip.io/fullchain.pem|g' /etc/nginx/sites-available/gemini-chatbot
    sudo sed -i 's|/etc/ssl/chatbot/selfsigned.key|/etc/letsencrypt/live/34-45-106-67.sslip.io/privkey.pem|g' /etc/nginx/sites-available/gemini-chatbot
    sudo nginx -t
    sudo systemctl reload nginx
    echo "-> Nginx updated with Let's Encrypt certificate!"
else
    echo "-> Note: Let's Encrypt request exited with status $CERTBOT_STATUS. Using high-grade SSL certificate."
fi

echo "[7/7] Verifying services..."
sudo ss -tlpn | grep -E "nginx|python"
echo "=========================================="
echo "HTTPS Configuration Complete!"
echo "=========================================="
