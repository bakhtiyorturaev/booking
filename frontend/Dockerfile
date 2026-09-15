# Multi-stage Dockerfile for Nuxt 4 Frontend
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (better cache layer)
COPY package*.json ./
RUN npm ci

# Copy project source
COPY . .

# Build Nuxt application for production
RUN npm run build

# Production runtime image
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0

# Copy output build from builder
COPY --from=builder /app/.output ./.output
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
