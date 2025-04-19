## MCP Gmail Server

This repository provides an MCP (Model Context Protocol) server for Gmail, enabling you to interact with your Gmail account through defined tools (`list_unread`, `search_emails`) over the MCP protocol. It handles OAuth2 authentication with Google and exposes an asyncio-based server for integration with Open WebUI or other MCP clients.

### Features

- **list_unread**: Retrieve snippets of unread Gmail messages.
- **search_emails**: Search emails by Gmail query (e.g., `from:alice@example.com`).
- Seamless OAuth2 flow with token caching.
- Asyncio-based server compatible with MCP clients (e.g., Open WebUI).

---

## What is MCP?

The Model Context Protocol (MCP) is an open standard that defines how applications provide context to large language models (LLMs). Think of MCP as a standardized interface—similar to USB-C for hardware—that allows AI models to connect with various tools and data sources seamlessly. 

---

## Why Use `mcpo`?

While MCP servers are powerful, they typically communicate via standard input/output (stdio), which can be limiting:

- Insecure across different environments.
- Incompatible with many modern tools, UIs, or platforms.
- Lack features like authentication, documentation, and error handling.

`mcpo` (MCP-to-OpenAPI proxy) addresses these issues by:

- Wrapping your MCP tools with secure, scalable HTTP endpoints.
- Making them instantly compatible with existing OpenAPI tools, SDKs, and clients.
- Auto-generating interactive OpenAPI documentation for each tool.
- Using plain HTTP—eliminating the need for socket setup or platform-specific code.

This means you can deploy your AI tools in the cloud, integrate them with web interfaces like Open WebUI, and enhance security and scalability—all without modifying your existing MCP server code. 

---

## Exposing MCP Gmail Server via `mcpo`

To expose your MCP Gmail Server through OpenAPI using `mcpo`, follow these steps:

1. **Install `mcpo`**:

   Using `pip`:

   ```bash
   pip install mcpo
   ```


   Or using `uv` (recommended for faster startup):

   ```bash
   uv pip install mcpo
   ```


2. **Run the MCP Gmail Server with `mcpo`**:

   ```bash
   mcpo --port 8000 -- uv run gmail-server
   ```


   This command starts the `mcpo` proxy on port 8000 and runs your Gmail MCP server behind it.

3. **Access the OpenAPI Documentation**:

   Once running, navigate to [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to view the auto-generated OpenAPI documentation for your Gmail tools.

4. **Integrate with Open WebUI**:

   In Open WebUI, add your new OpenAPI tool server by specifying the endpoint (e.g., `http://localhost:8000`). This allows you to interact with your Gmail account through the Open WebUI interface using the defined tools.

---

By integrating `mcpo` with your MCP Gmail Server, you enhance its accessibility, security, and compatibility with modern tools and platforms, facilitating seamless interactions with your Gmail account through standardized APIs.

--- 

## Prerequisites

- Python 3.13 or newer
- [uv](https://github.com/astral-sh/uv) package manager
- A Google account
- Access to create projects and OAuth credentials on Google Cloud Console

## Project Structure

```
├── mcp_server/
│   ├── __init__.py       # Package initialization
│   └── gmail/
│       ├── __init__.py   # Module initialization
│       └── server.py     # Main server implementation
├── tests/
│   ├── __init__.py
│   └── test_gmail_server.py  # Test suite for Gmail server
├── secrets/
│   ├── credentials.json  # OAuth2 client credentials (downloaded)
│   └── token.json        # Cached user tokens (auto-created)
├── pyproject.toml        # Project metadata and dependencies
├── pytest.ini           # Pytest configuration
├── run_tests.sh         # Script to run tests with uv
├── Dockerfile           # Docker configuration
└── README.md            # This documentation
```

## Gmail API Credential Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Create a new project (or select an existing one).
3. **Enable** the Gmail API under **APIs & Services > Library**.
4. Under **APIs & Services > OAuth consent screen**, configure an **External** consent screen:
   - App name: `MCP Gmail Server`
   - Add your email as a **Test user** (the server won't be published).
5. Under **APIs & Services > Credentials**, click **Create Credentials > OAuth client ID**.
   - Application type: **Desktop app**
   - Download the JSON file.
6. Rename the downloaded file to `credentials.json` and place it in the `secrets/` directory.

## Installation

1. Clone this repository:


2. Install `uv` if you don't have it yet:

   ```bash
   pipx install uv
   ```

3. Create and activate a virtual environment using `uv`:

   ```bash
   # Create a virtual environment
   uv venv
   
   # Activate the virtual environment
   # On Unix/macOS:
   source .venv/bin/activate
   
   # On Windows:
   .\.venv\Scripts\activate
   ```

4. Install dependencies using `uv`:

   ```bash
   # Install the package in development mode
   uv pip install -e .
   ```

## Configuration

- Ensure the `secrets/credentials.json` file is present.
- The first run will prompt you to authorize the app in your browser; afterwards, a `secrets/token.json` file is created.

## Running the Server

Start the MCP server via:

```bash
# Run directly with uv
uv run gmail-server

# Alternative: Run with MCP OpenAPI Proxy
uvx mcpo --port 8000 --api-key "your-api-key" -- uv run gmail-server
```

You should see output indicating the server is running and listening for MCP client connections.

## Usage

- Connect any MCP-compliant client (e.g., [Open Web UI](https://docs.openwebui.com/openapi-servers/mcp/)).
- Use the following tools/actions:
  - **list_unread**: Returns unread email snippets.
  - **search_emails**: Returns emails matching the provided Gmail query.

## Docker Setup

The project includes a Dockerfile for containerization:

1. **Build the Docker image**:

   ```bash
   docker build -t gmail-mcp-server .
   ```

2. **Run the Docker container**:

   ```bash
   docker run -p 8000:8000 \
     -e API_KEY="your-secure-api-key" \
     gmail-mcp-server
   ```

### Docker Configuration Details

- **Base Image**: Python 3.13-slim
- **Dependencies**: Installed using `uv`
- **Volume Mount**: `/app/secrets` should contain your Google OAuth credentials
- **Environment Variables**:
  - `API_KEY`: Security key for the MCP OpenAPI proxy (default: "top-secret")
- **Port**: Exposes port 8000 for the MCP OpenAPI proxy

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

