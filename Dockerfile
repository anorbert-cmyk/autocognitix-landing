FROM nginx:alpine

# Install Python3 + proxy deps (OPTIONAL — build continues even if pip fails)
RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir --break-system-packages \
      httpx==0.27.0 uvicorn==0.27.1 starlette==0.36.3 2>/dev/null || \
    echo "WARNING: Proxy deps install failed — proxy will be disabled, nginx still works" && \
    mkdir -p /opt/proxy

# Copy proxy code (will only be used if deps installed successfully)
COPY proxy/main.py /opt/proxy/main.py

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy SEO files
COPY sitemap.xml /usr/share/nginx/html/sitemap.xml
COPY robots.txt /usr/share/nginx/html/robots.txt

# Copy site files
COPY hu/ /usr/share/nginx/html/hu/
COPY en/ /usr/share/nginx/html/en/
COPY shared/ /usr/share/nginx/html/shared/
COPY unsubscribe.html /usr/share/nginx/html/unsubscribe.html

# Startup script (starts proxy only if deps available, nginx always starts)
COPY start.sh /start.sh
RUN chmod +x /start.sh

ENV PORT=8080
ENV BACKEND_URL=https://autocognitix-production.up.railway.app
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s CMD wget --no-verbose --tries=1 --spider http://localhost:8080/hu/ || exit 1

CMD ["/start.sh"]
