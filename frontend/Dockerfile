# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM node:20-alpine AS builder

WORKDIR /app

# Dépendances (layer isolé)
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline

# Source
COPY . .

# Build SvelteKit (adapter-static)
RUN npm run build

# ---- Serve stage ----
# nginx:alpine = ~23 MB, bien plus léger que node pour servir du statique
FROM nginx:1.27-alpine AS runner

# Conf nginx custom : SPA fallback + gzip + cache assets
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copie du build SvelteKit
COPY --from=builder /app/build /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/health.txt || exit 1

CMD ["nginx", "-g", "daemon off;"]
