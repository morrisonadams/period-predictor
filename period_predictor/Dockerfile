ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# Install Node.js
RUN apk add --no-cache nodejs npm

WORKDIR /app
COPY backend /app/backend
COPY web /app/web
RUN npm --prefix backend install \
    && npm --prefix web install

COPY rootfs /

EXPOSE 3002
