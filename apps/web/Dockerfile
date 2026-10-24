ARG WEB_BASE_IMAGE=node:22-alpine
FROM ${WEB_BASE_IMAGE}

WORKDIR /app

COPY apps/web/scripts/check-runtime.cjs ./scripts/check-runtime.cjs
RUN node scripts/check-runtime.cjs

COPY apps/web/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
RUN npm audit

COPY apps/web ./
ARG API_INTERNAL_URL=http://api:8000
ENV API_INTERNAL_URL=${API_INTERNAL_URL}
RUN npm test && npm run typecheck && npm run build

EXPOSE 3000

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
