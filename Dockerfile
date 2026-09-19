
FROM node:20-alpine AS frontend-builder
WORKDIR /app/Front
COPY Front/package*.json ./
RUN npm install
COPY Front/ .
RUN npm run build

FROM python:3.10-slim
WORKDIR /app/Back

ENV PYTHONUNBUFFERED=1

COPY Back/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Back/ /app/Back/
COPY --from=frontend-builder /app/Front/dist /app/Front/dist

EXPOSE 80

RUN mkdir -p /data/uploads

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]