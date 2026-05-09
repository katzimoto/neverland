FROM nginx:1.27-alpine AS runtime

COPY docker/frontend-nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/static /usr/share/nginx/html

EXPOSE 8080
