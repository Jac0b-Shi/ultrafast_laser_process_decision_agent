ARG WEB_BASE_IMAGE=node:22-alpine
FROM ${WEB_BASE_IMAGE}

WORKDIR /app

COPY apps/web/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY apps/web ./

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
