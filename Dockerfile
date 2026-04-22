# Pinned base image for reproducible builds (DEVOPS-H1).
# Wave 5: bumped from nginx:1.27-alpine3.19 to nginx:1.29-alpine3.22 to pick up
# ~15 Alpine distro CVE patches (libxml2, libssl3, musl, xz-libs, libexpat).
# Alpine 3.22 ships Python 3.12 with a matching libexpat that no longer has
# the 3.20 ABI mismatch that broke Wave 4.
FROM nginx:1.29-alpine3.22

# Install Python3 + proxy deps — mandatory, no silent failure (DEVOPS-C2).
# Wave 5: `apk upgrade` first so we pick up the latest distro patches that
# landed after the nginx:1.29-alpine3.22 base tag was published. Trivy blocks
# on HIGH+CRITICAL; the base tag is frozen, so weekly CVE fixes otherwise
# pile up until Docker Hub rebuilds. `--no-cache` + `apk cache clean` keeps
# the image small.
RUN apk upgrade --no-cache \
    && apk add --no-cache python3 py3-pip \
    && rm -rf /var/cache/apk/* \
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
# The official nginx:alpine image already ships with a `nginx` user (uid 101)
# and `nginx` group (gid 101). Reuse them instead of creating an overlapping
# 'app' user (which would collide on -u 101 and break the build).
# /run is where nginx writes its pid; must be writable by the runtime user.
RUN touch /run/nginx.pid \
    && chown -R nginx:nginx \
         /usr/share/nginx/html \
         /var/cache/nginx \
         /var/log/nginx \
         /etc/nginx/conf.d \
         /opt/proxy \
         /run/nginx.pid

USER nginx

# Dev default; Railway injects real value at deploy time (DEVOPS-L1).
# BACKEND_URL is intentionally NOT set here — proxy/main.py fail-fasts when
# ENVIRONMENT=production and BACKEND_URL is missing, preventing a staging
# container from silently pointing at the prod backend.
ENV PORT=8080
ENV ENVIRONMENT=production
EXPOSE 8080

# Composite healthcheck: both nginx AND proxy sidecar must be healthy (DEVOPS-H2)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:8080/hu/ \
        && wget -q --spider http://localhost:8080/proxy/health \
        || exit 1

CMD ["/start.sh"]
