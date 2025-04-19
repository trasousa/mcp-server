# src/mcp_server/gmail/gmail_client.py
import sys
from typing import Optional, List, Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

class GmailApiClient:
    """Handles interactions with the Gmail API."""

    def __init__(self, credentials: Credentials):
        """
        Initializes the Gmail API client.

        Args:
            credentials: Valid Google OAuth2 credentials.

        Raises:
            ValueError: If invalid or missing credentials are provided.
        """
        if not credentials or not credentials.valid:
            raise ValueError("Invalid or missing credentials provided to GmailApiClient.")
        try:
            self.service: Resource = build("gmail", "v1", credentials=credentials)
            print("Gmail API service built successfully.")
        except Exception as e:
            print(f"Error building Gmail service: {e}", file=sys.stderr)
            raise RuntimeError(f"Could not build Gmail service: {e}") from e

    def list_message_ids(self, query: Optional[str] = None, label_ids: Optional[List[str]] = None, max_results: int = 10) -> List[Dict[str, str]]:
        """
        Lists message IDs matching the criteria.

        Args:
            query: Gmail search query (e.g., 'from:me').
            label_ids: List of label IDs (e.g., ['UNREAD']).
            max_results: Maximum number of messages to return.

        Returns:
            A list of message dictionaries (e.g., [{'id': '...', 'threadId': '...'}]),
            or an empty list if none found.

        Raises:
            HttpError: If the API call fails.
        """
        print(f"Listing messages with query='{query}', labels={label_ids}, max_results={max_results}")
        try:
            request = self.service.users().messages().list(
                userId="me",
                q=query,
                labelIds=label_ids,
                maxResults=max_results
            )
            response = request.execute()
            messages = response.get("messages", [])
            print(f"Found {len(messages)} message IDs.")
            return messages
        except HttpError as error:
             print(f"API Error listing messages: {error}", file=sys.stderr)
             # Let HttpError propagate - the caller (_execute_tool) might handle it
             raise error

    def get_message_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches and parses details for a specific message ID.

        Args:
            message_id: The ID of the message to fetch.

        Returns:
            A dictionary containing parsed details (id, subject, from, date, snippet)
            or None if the message cannot be fetched or parsed due to errors.
        """
        print(f"Fetching details for message ID: {message_id}")
        try:
            msg = self.service.users().messages().get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"]
            ).execute()

            headers = msg.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown")
            snippet = msg.get("snippet", "")

            print(f"Successfully fetched details for message ID: {message_id}")
            return {
                "id": message_id, # Use the requested ID
                "subject": subject,
                "from": sender,
                "date": date,
                "snippet": snippet,
            }
        except HttpError as error:
            # Log HttpError specifically (e.g., 404 Not Found) and return None
            print(f"API Error fetching message {message_id}: {error}", file=sys.stderr)
            return None
        except Exception as e:
            # Catch any other unexpected errors during processing/parsing
            print(f"Unexpected error processing message {message_id}: {e}", file=sys.stderr)
            return None