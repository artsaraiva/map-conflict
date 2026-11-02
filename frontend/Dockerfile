FROM node:20-bookworm-slim

WORKDIR /app/frontend

COPY frontend/package*.json ./

RUN npm ci

COPY frontend /app/frontend

EXPOSE 3001
