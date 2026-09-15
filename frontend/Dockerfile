# Multi-stage Dockerfile for Nuxt 4 Frontend
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy project source
COPY . .

# Prepare Nuxt and build application for production
RUN npx nuxt prepare && npm run build

# Production runtime image
FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0 \
    NITRO_HOST=0.0.0.0 \
    NITRO_PORT=3000

# Copy output build from builder
COPY --from=builder /app/.output ./.output
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

CMD node .output/server/index.mjs
