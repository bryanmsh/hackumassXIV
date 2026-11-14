# Caddy with the built web app inside. Build context is the repo root:
#   docker compose build caddy

FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
# VITE_API_URL is left empty: a production build then calls same-origin /api.
RUN npm run build

FROM caddy:2
COPY --from=web /web/dist /srv
COPY infra/caddy-start.sh /usr/local/bin/caddy-start
RUN chmod +x /usr/local/bin/caddy-start
CMD ["caddy-start"]
