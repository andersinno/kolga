# ===================================
FROM alpine:latest AS staticbuilder
# ===================================

WORKDIR /app/html
RUN echo "Hello world" >> /app/index.html

# ===================================
FROM nginx:1.17-alpine AS webserver
# ===================================

COPY --from=staticbuilder /app /usr/share/nginx/html
