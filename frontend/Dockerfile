# Frontend Dockerfile for Railway
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY bun.lock* ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Set production API URL for Vite build
ENV VITE_API_BASE_URL=https://api.tokenspender.com/api

# Build the app
RUN npm run build

# Production stage
FROM node:20-slim

WORKDIR /app

# Install serve globally
RUN npm install -g serve

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Expose port (Railway sets PORT env variable)
EXPOSE 3000

# Start the server
CMD ["sh", "-c", "serve dist -s -l ${PORT:-3000}"]
