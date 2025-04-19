# src/mcp_server/gmail/server.py
import json
import asyncio
import sys
from pathlib import Path
from typing import List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# build and HttpError are no longer directly needed here
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import the new client
from .gmail_client import GmailApiClient
# Import HttpError to potentially catch errors propagated from the client
from googleapiclient.errors import HttpError


# --- Constants ---
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
# Ensure BASE_DIR points to your actual project root if structure differs
# Example: if this file is src/mcp_server/gmail/server.py, then parent.parent.parent is correct
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRETS_DIR = BASE_DIR / "secrets"
TOKEN_FILE = SECRETS_DIR / "token.json"
CREDENTIALS_FILE = SECRETS_DIR / "credentials.json"

# --- Credentials Function ---
def get_credentials():
    """Get valid user credentials from storage or through OAuth flow."""
    creds = None
    print(f"Secrets directory: {SECRETS_DIR}")
    SECRETS_DIR.mkdir(parents=True, exist_ok=True) # Ensure parent dirs exist

    # Load existing credentials from JSON file
    if TOKEN_FILE.exists():
        print(f"Token file found at {TOKEN_FILE}, attempting to load.")
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            print("Credentials loaded from token file.")
        except Exception as e:
            print(f"Error loading credentials from token file: {e}", file=sys.stderr)
            creds = None # Ensure creds is None if loading failed
    else:
        print(f"Token file not found at {TOKEN_FILE}.")

    # If no valid credentials, go through OAuth flow or refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Credentials expired, attempting to refresh...")
            try:
                creds.refresh(Request())
                print("Credentials refreshed successfully.")
            except Exception as e:
                print(f"Failed to refresh token: {e}", file=sys.stderr)
                # Force re-auth if refresh fails
                creds = None
                print("Refresh failed, proceeding to OAuth flow.")
        else:
             # This branch is hit if no creds loaded, or creds are invalid without refresh token
             print("No valid credentials found, initiating OAuth flow.")

        # Re-check creds after potential refresh attempt or if initial load failed
        if not creds or not creds.valid:
            if not CREDENTIALS_FILE.exists():
                print(f"Credentials file missing at {CREDENTIALS_FILE}", file=sys.stderr)
                raise FileNotFoundError(
                    f"Credentials file not found at {CREDENTIALS_FILE}. "
                    "Please download OAuth 2.0 Client ID credentials (Desktop app) "
                    "from Google Cloud Console and save as 'credentials.json' in the 'secrets' directory."
                )

            print(f"Using credentials file: {CREDENTIALS_FILE}")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                print("Starting local server for OAuth authentication...")
                # run_local_server will print instructions and open a browser
                creds = flow.run_local_server(port=0)
                print("OAuth flow completed, credentials obtained.")
            except Exception as e:
                 print(f"Error during OAuth flow: {e}", file=sys.stderr)
                 raise RuntimeError(f"OAuth flow failed: {e}") from e

        # Save the potentially new or refreshed credentials
        if creds:
             try:
                 with open(TOKEN_FILE, "w") as token:
                     token.write(creds.to_json())
                 print(f"Credentials saved to {TOKEN_FILE}")
             except Exception as e:
                 print(f"Error saving token file {TOKEN_FILE}: {e}", file=sys.stderr)
                 # Don't raise here, we might still have valid creds in memory

    # Final check
    if not creds or not creds.valid:
         raise RuntimeError("Failed to obtain valid credentials after all attempts.")

    print("Credentials ready.")
    return creds


# --- Tool Definitions (Removed 'required' field) ---
async def _get_tool_definitions() -> list[Tool]:
    """Returns the list of tool definitions."""
    return [
        Tool(
            name="list_unread",
            description="List unread Gmail message snippets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of messages to return (default: 10)",
                    }
                },
            },
        ),
        Tool(
            name="search_emails",
            description="Search emails with a Gmail query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query (e.g. 'from:someone@example.com')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of messages to return (default: 10)",
                    },
                },
                # "required": ["query"], # REMOVED this line to fix Pydantic validation
            },
        ),
    ]


# --- Execute Tool (Uses GmailApiClient) ---
async def _execute_tool(name: str, arguments: dict, client: GmailApiClient) -> list[TextContent]:
    """
    Executes the specified tool logic using the GmailApiClient.

    Args:
        name: The name of the tool to execute.
        arguments: The arguments for the tool.
        client: An initialized GmailApiClient instance.

    Returns:
        A list containing one TextContent object with the results.

    Raises:
         ValueError: If the tool name is unknown or required arguments are missing.
         HttpError: If the underlying API list calls fail.
    """
    output = []
    message_ids = []

    try:
        if name == "list_unread":
            max_results = arguments.get("max_results", 10)
            print(f"Calling client.list_message_ids for UNREAD (max: {max_results})")
            # Call client method, can raise HttpError
            message_ids = await asyncio.to_thread(client.list_message_ids, label_ids=["UNREAD"], max_results=max_results)

        elif name == "search_emails":
            query = arguments.get("query")
            # Check for missing or empty query, since schema doesn't enforce 'required'
            if not query:
                raise ValueError("Missing or empty required argument: query")
            max_results = arguments.get("max_results", 10)
            print(f"Calling client.list_message_ids for query='{query}' (max: {max_results})")
             # Call client method, can raise HttpError
            message_ids = await asyncio.to_thread(client.list_message_ids, query=query, max_results=max_results)

        else:
            raise ValueError(f"Unknown tool: {name}")

        # Process message IDs returned by the client
        if message_ids:
            print(f"Found {len(message_ids)} messages for tool '{name}'. Fetching details...")
            tasks = []
            for msg_ref in message_ids:
                # Fetch details concurrently using asyncio.to_thread
                tasks.append(asyncio.to_thread(client.get_message_details, msg_ref['id']))

            # Gather results from concurrent fetches
            details_results = await asyncio.gather(*tasks)

            for details in details_results:
                if details:
                    output.append(details)
                else:
                    # Append a placeholder if fetching details failed (client returned None)
                    # Find the ID that corresponds to this None result (tricky without tracking)
                    # For simplicity, just log that *a* fetch failed. Better tracking needed for exact ID.
                    print("Warning: Failed to fetch details for one or more messages.", file=sys.stderr)
                    output.append({
                         "id": "unknown", # We don't easily know which ID failed here
                         "error": "Failed to fetch message details",
                         "subject": "Error", "from": "Error", "date": "Error", "snippet": ""
                     })
        else:
             print(f"No messages found for tool '{name}'.")

    except HttpError as e:
        # Handle API errors specifically during list calls
        print(f"API error during tool execution '{name}': {e}", file=sys.stderr)
        # Re-raise to be potentially caught by serve() or return specific error text
        error_message = f"Gmail API Error: {e.resp.status} {e.reason}"
        return [TextContent(type="text", text=json.dumps({"error": error_message}))]
    except ValueError as e:
        # Handle ValueErrors (unknown tool, missing args)
        print(f"Value error during tool execution '{name}': {e}", file=sys.stderr)
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    except Exception as e:
        # Catch other potential errors
        print(f"Unexpected error during tool execution '{name}': {e}", file=sys.stderr)
        return [TextContent(type="text", text=json.dumps({"error": f"Internal server error: {e}"}))]


    print(f"Tool '{name}' execution finished. Returning {len(output)} messages.")
    return [
        TextContent(
            type="text", text=json.dumps({"messages": output}, indent=2)
        )
    ]


# --- Server Setup ---
async def serve():
    """Main server function for the MCP Gmail integration."""
    client = None # Initialize client to None
    try:
        print("Attempting to get credentials...")
        # Run blocking IO in a separate thread
        creds = await asyncio.to_thread(get_credentials)
        print("Credentials obtained successfully.")

        # Create the client instance here (also potentially blocking if build() is slow)
        # Although build is usually fast, let's keep it potentially async friendly
        client = await asyncio.to_thread(GmailApiClient, credentials=creds)
        print("GmailApiClient initialized.")

        server = Server(name="mcp-gmail")

        @server.list_tools()
        async def list_tools() -> list[Tool]:
            # No change here, it's fast
            return await _get_tool_definitions()

        @server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            # Pass the initialized client instance
            if client is None:
                 # This should ideally not happen if serve() setup works
                 print("CRITICAL: Gmail API Client was not initialized!", file=sys.stderr)
                 return [TextContent(type="text", text=json.dumps({"error": "Server not initialized correctly."}))]
            print(f"Executing tool: {name} with args: {arguments}")
            # _execute_tool now handles its own errors and returns TextContent list
            return await _execute_tool(name, arguments, client)

        options = server.create_initialization_options()
        print("Starting MCP server via stdio...")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, options)
        print("MCP server finished.")

    except FileNotFoundError as e:
         # Raised by get_credentials if credentials.json is missing
         print(f"Configuration Error: {e}", file=sys.stderr)
         # Exit cleanly if critical config is missing
         sys.exit(1)
    except RuntimeError as e:
         # Raised if credentials could not be obtained/refreshed/validated
         print(f"Initialization Error: {e}", file=sys.stderr)
         sys.exit(1)
    except Exception as e:
        # Catch unexpected errors during server startup or shutdown
        print(f"FATAL Error running Gmail MCP server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        # Re-raise or specific exit codes depending on desired behavior
        raise # Re-raise to potentially be caught by main()


# --- Main Entry Point ---
def main():
    """Entry point for the MCP server that properly handles the asyncio event loop."""
    try:
        print("Starting Gmail MCP Server...")
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except Exception as e:
        # Catch errors raised from serve() or asyncio itself
        print(f"\nUnhandled error during server execution: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        print("Gmail MCP Server exited.")


if __name__ == "__main__":
    main()