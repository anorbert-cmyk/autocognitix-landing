# Pinned base image for reproducible builds (DEVOPS-H1)
FROM nginx:1.27-alpine3.20

# Install Python3 + proxy deps — mandatory, no silent failure (DEVOPS-C2)
# Uses apk version pin matching alpine3.20 repo (~3.12 family)
RUN apk add --no-cache python3=~3.12 py3-pip \
    && mkdir -p /opt/proxy

# Copy requirements first for layer caching (DEVOPS-M1)
COPY proxy/requirements.txt /opt/proxy/requirements.txt

# Install pinned Python deps from requirements.txt (DEVOPS-M1, C2)
# --break-system-packages is required on Alpine py3-pip (PEP 668)
# Failure here now fails the build, as intended.
RUN pip3 install --no-cache-dir --break-system-packages -r /opt/proxy/requirements.txt

# Copy proxy application code
COPY proxy/main.py /opt/proxy/main.py

# Remove default nginx config and install custom one
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy SEO files
COPY sitemap.xml /usr/share/nginx/html/sitemap.xml
COPY robots.txt /usr/share/nginx/html/robots.txt

# Copy site files
COPY hu/ /usr/share/nginx/html/hu/
COPY en/ /usr/share/nginx/html/en/
COPY shared/ /usr/share/nginx/html/shared/
COPY unsubscribe.html /usr/share/nginx/html/unsubscribe.html

# Startup script (graceful signal handling, fail-fast)
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Non-root runtime (DEVOPS-C1)
# The official nginx:alpine image already has a `nginx` user (uid 101).
# Create an 'app' group/user aligned with that uid, and chown runtime dirs.
# /run is where nginx writes its pid; must be writable by the runtime user.
RUN addgroup -S app 2>/dev/null || true \
    && adduser -S -D -H -u 101 -G app -s /sbin/nologin app 2>/dev/null || true \
    && touch /run/nginx.pid \
    && chown -R app:app \
         /usr/share/nginx/html \
         /var/cache/nginx \
         /var/log/nginx \
         /etc/nginx/conf.d \
         /opt/proxy \
         /run/nginx.pid

USER app

# Dev default; Railway injects real value at deploy time (DEVOPS-L1)
ENV PORT=8080
ENV BACKEND_URL=https://autocognitix-production.up.railway.app
EXPOSE 8080

# Composite healthcheck: both nginx AND proxy sidecar must be healthy (DEVOPS-H2)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:8080/hu/ \
        && wget -q --spider http://localhost:8080/proxy/health \
        || exit 1

CMD ["/start.sh"]
