# SecureShare Messenger - Production Deployment Guide

## 1. Prerequisites
- Linux / Windows server with Python 3.10+
- MongoDB Atlas cluster URL (`mongodb+srv://...`)
- Registered domain with TLS certificate (Let's Encrypt)
- NGINX reverse proxy

## 2. Environment Configuration
Create a production `.env` file:
```env
SECRET_KEY=generate-a-strong-random-hex-string-using-secrets-token-hex-32
FLASK_ENV=production
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/secureshare?retryWrites=true&w=majority
MONGO_DB_NAME=secureshare
PORT=5000
HOST=0.0.0.0
```

## 3. WSGI Server Configuration
Run with Gunicorn using an asynchronous worker (Eventlet or Gevent):
```bash
pip install gunicorn eventlet
gunicorn -k eventlet -w 1 app:app --bind 127.0.0.1:5000
```

## 4. NGINX Reverse Proxy with WebSocket Upgrade
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
