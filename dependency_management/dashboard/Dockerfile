# Use Node.js 18 image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package file
COPY dashboard/package.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY dashboard/ .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Run the application
CMD ["npm", "start"]
