# Use Node.js 18 Alpine
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files for dependency caching
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY src/ ./src/
COPY .env ./

# Expose port
EXPOSE 5000

# Start the application
CMD ["node", "src/server.js"]