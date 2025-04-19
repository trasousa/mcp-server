FROM python:3.13-slim

WORKDIR /app

# Install uv and other required tools
RUN pip install --no-cache-dir uv
RUN pip install --no-cache-dir mcpo  # Install mcpo to provide the uvx command

# Copy all project files
COPY . .

# Create virtual environment and install dependencies
RUN uv venv
# Install the package in regular mode (not editable) for Docker
RUN . .venv/bin/activate && uv pip install .

# Create the secrets directory if it doesn't exist
RUN mkdir -p secrets

# Expose the port used by mcpo
EXPOSE 8000

# Set a default API key (this should be overridden at runtime)
ENV API_KEY="default-replace-me"

# Run the server with mcpo
CMD ["sh", "-c", ". .venv/bin/activate && uvx mcpo --port 8000 --host 0.0.0.0 --api-key \"${API_KEY}\" -- uv run gmail-server"]