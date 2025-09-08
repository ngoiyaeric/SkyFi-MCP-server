# Stage 1: Build the Docusaurus static site
FROM node:18-alpine AS docusaurus-builder
WORKDIR /app
COPY docusaurus/package.json docusaurus/package-lock.json ./
RUN npm install
COPY docusaurus/ .
# Set the baseUrl to /docs/ so that the site is served from a sub-path
RUN sed -i "s|baseUrl: '/'|baseUrl: '/docs/'|" docusaurus.config.js
RUN npm run build

# Stage 2: Install Python dependencies
FROM python:3.10-slim AS python-builder
WORKDIR /app
COPY pyproject.toml .
COPY README.md .
# Copy the source code for the python application
COPY src ./src
# Install the application and its dependencies
RUN pip install .

# Stage 3: Final image with Nginx and the application
FROM python:3.10-slim
WORKDIR /app

# Install Nginx
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

# Copy the Python application and its dependencies from the python-builder stage
COPY --from=python-builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=python-builder /usr/local/bin/mcp-skyfi /usr/local/bin/mcp-skyfi

# Copy the built Docusaurus site from the docusaurus-builder stage
# The static files will be served by Nginx from the /docs/ path
COPY --from=docusaurus-builder /app/build /var/www/html/docs

# Copy the Nginx configuration and entrypoint script
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose port 80 for Nginx
EXPOSE 80

# Set the entrypoint to our script
ENTRYPOINT ["/app/entrypoint.sh"]
