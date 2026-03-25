FROM nginx:1.27-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy SEO files
COPY sitemap.xml /usr/share/nginx/html/sitemap.xml
COPY robots.txt /usr/share/nginx/html/robots.txt

# Copy site files
COPY hu/ /usr/share/nginx/html/hu/
COPY en/ /usr/share/nginx/html/en/
COPY shared/ /usr/share/nginx/html/shared/
COPY unsubscribe.html /usr/share/nginx/html/unsubscribe.html

# Railway uses PORT env var
ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s CMD wget --no-verbose --tries=1 --spider http://localhost:8080/hu/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
