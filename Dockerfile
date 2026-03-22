FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy SEO files
COPY sitemap.xml /usr/share/nginx/html/sitemap.xml
COPY robots.txt /usr/share/nginx/html/robots.txt

# Copy only the site files (hu/ and en/ folders)
COPY hu/ /usr/share/nginx/html/hu/
COPY en/ /usr/share/nginx/html/en/

# Railway uses PORT env var
ENV PORT=8080
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
