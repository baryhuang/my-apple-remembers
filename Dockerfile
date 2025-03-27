# Use Python base image
FROM python:3.10-slim

# Install the project into `/app`
WORKDIR /app

# Copy the entire project
COPY . .

# Install the package
RUN pip install -e .

# Run the server
CMD ["python", "-m", "mcp_my_apple_remembers.server"] 