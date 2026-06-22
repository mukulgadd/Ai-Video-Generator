"""Notification adapters for the Ramayan Video Generator.

Provides email and webhook notification adapters for pipeline failure
alerts. Uses a Protocol-based design for extensibility and testability.

Validates: Requirements 1.5
"""

import json
import logging
import smtplib
from dataclasses import dataclass
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Protocol

import requests

from src.config_loader import NotificationsConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class NotificationError(Exception):
    """Raised when a notification fails to send."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class PipelineFailureAlert:
    """Details of a pipeline failure for notification."""

    stage_name: str
    error_message: str
    episode_number: int
    kanda_name: str
    retry_attempts: int


# ---------------------------------------------------------------------------
# NotificationSender Protocol
# ---------------------------------------------------------------------------


class NotificationSender(Protocol):
    """Protocol for notification delivery backends."""

    def send(self, alert: PipelineFailureAlert) -> bool:
        """Send a failure notification.

        Args:
            alert: The pipeline failure details.

        Returns:
            True if the notification was sent successfully, False otherwise.
        """
        ...


# ---------------------------------------------------------------------------
# Email Adapter
# ---------------------------------------------------------------------------


class EmailNotificationAdapter:
    """Sends pipeline failure alerts via email.

    In production, this uses SMTP to send emails. For testing and
    development, it logs the notification details.

    Args:
        recipients: List of email addresses to notify.
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port.
        sender: Sender email address.
    """

    def __init__(
        self,
        recipients: List[str],
        smtp_host: str = "localhost",
        smtp_port: int = 25,
        sender: str = "ramayan-pipeline@example.com",
    ):
        self._recipients = recipients
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._sender = sender

    def send(self, alert: PipelineFailureAlert) -> bool:
        """Send a failure notification via email.

        Args:
            alert: The pipeline failure details.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        subject = (
            f"[Ramayan Pipeline] Stage '{alert.stage_name}' failed "
            f"- Episode {alert.episode_number}"
        )
        body = (
            f"Pipeline Failure Alert\n"
            f"======================\n\n"
            f"Stage: {alert.stage_name}\n"
            f"Episode: {alert.episode_number}\n"
            f"Kanda: {alert.kanda_name}\n"
            f"Retry Attempts: {alert.retry_attempts}\n"
            f"Error: {alert.error_message}\n"
        )

        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self._sender
            msg["To"] = ", ".join(self._recipients)

            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.sendmail(self._sender, self._recipients, msg.as_string())

            logger.info(
                "Email notification sent to %s for stage '%s' failure",
                self._recipients,
                alert.stage_name,
            )
            return True
        except Exception as e:
            logger.error("Failed to send email notification: %s", e)
            return False


# ---------------------------------------------------------------------------
# Webhook Adapter
# ---------------------------------------------------------------------------


class WebhookNotificationAdapter:
    """Sends pipeline failure alerts via webhook (HTTP POST).

    Posts a JSON payload to the configured webhook URL.

    Args:
        webhook_url: The URL to POST failure alerts to.
        headers: Optional additional HTTP headers.
    """

    def __init__(
        self,
        webhook_url: str,
        headers: Optional[Dict[str, str]] = None,
    ):
        self._webhook_url = webhook_url
        self._headers = headers or {"Content-Type": "application/json"}

    def send(self, alert: PipelineFailureAlert) -> bool:
        """Send a failure notification via webhook.

        Args:
            alert: The pipeline failure details.

        Returns:
            True if the webhook call succeeded, False otherwise.
        """
        payload = {
            "event": "pipeline_failure",
            "stage_name": alert.stage_name,
            "error_message": alert.error_message,
            "episode_number": alert.episode_number,
            "kanda_name": alert.kanda_name,
            "retry_attempts": alert.retry_attempts,
        }

        try:
            response = requests.post(
                self._webhook_url,
                json=payload,
                headers=self._headers,
                timeout=10,
            )
            response.raise_for_status()

            logger.info(
                "Webhook notification sent to %s for stage '%s' failure",
                self._webhook_url,
                alert.stage_name,
            )
            return True
        except Exception as e:
            logger.error("Failed to send webhook notification: %s", e)
            return False


# ---------------------------------------------------------------------------
# Mock Adapter (for testing)
# ---------------------------------------------------------------------------


class MockNotificationAdapter:
    """Mock notification adapter that records sent alerts for testing."""

    def __init__(self):
        self.sent_alerts: List[PipelineFailureAlert] = []

    def send(self, alert: PipelineFailureAlert) -> bool:
        """Record the alert and return True."""
        self.sent_alerts.append(alert)
        logger.info(
            "Mock notification sent for stage '%s' failure (episode %d)",
            alert.stage_name,
            alert.episode_number,
        )
        return True


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_notification_sender(
    config: NotificationsConfig,
) -> Any:
    """Create a notification sender based on configuration.

    Args:
        config: NotificationsConfig with provider and recipients.

    Returns:
        A notification sender instance.
    """
    provider = config.provider.lower()

    if provider == "email":
        return EmailNotificationAdapter(recipients=config.recipients)
    elif provider == "webhook":
        # Webhook URL would come from an extended config; use first recipient as URL
        url = config.recipients[0] if config.recipients else "http://localhost/webhook"
        return WebhookNotificationAdapter(webhook_url=url)
    else:
        logger.warning(
            "Unknown notification provider '%s', using mock adapter",
            provider,
        )
        return MockNotificationAdapter()
