ARG WEB_BASE_IMAGE=node:22-alpine
FROM ${WEB_BASE_IMAGE}

WORKDIR /app

COPY apps/web/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
RUN npm audit --audit-level=high

COPY apps/web ./
ARG API_INTERNAL_URL=http://api:8000
ENV API_INTERNAL_URL=${API_INTERNAL_URL}
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
