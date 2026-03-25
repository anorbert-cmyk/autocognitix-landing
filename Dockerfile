FROM python:3.11-alpine AS proxy-build
WORKDIR /proxy
COPY proxy/requirements.txt .
RUN pip install --no-cache-dir --target=/proxy/deps -r requirements.txt

FROM nginx:1.27-alpine

# Install Python runtime only (no supervisor needed)
RUN apk add --no-cache python3

# Copy proxy deps and code
COPY --from=proxy-build /proxy/deps /opt/proxy/deps
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

# Startup script: proxy in background, nginx in foreground
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Railway uses PORT env var
ENV PORT=8080
ENV BACKEND_URL=https://autocognitix-production.up.railway.app
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s CMD wget --no-verbose --tries=1 --spider http://localhost:8080/hu/ || exit 1

CMD ["/start.sh"]
