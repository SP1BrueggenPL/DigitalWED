import logging
import os

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

logger = logging.getLogger(__name__)


def send_email(recipients, subject, body, attachments=None):
    """Wysyła e-mail przez Azure Communication Services. Zwraca True, gdy wysłano."""
    connection_string = os.environ.get('AZURE_CONNECTION_STRING', '')
    sender_address = os.environ.get('AZURE_SENDER_ADDRESS', '')
    if not connection_string or not sender_address:
        logger.warning('Email: brak AZURE_CONNECTION_STRING lub AZURE_SENDER_ADDRESS')
        return False
    recipients = list(recipients)
    if not recipients:
        logger.warning('Email: brak odbiorców w ustawieniach (%s)', subject)
        return False
    try:
        from azure.communication.email import EmailClient
        client = EmailClient.from_connection_string(connection_string)
        message = {
            'senderAddress': sender_address,
            'recipients': {'to': [{'address': addr} for addr in recipients]},
            'content': {'subject': subject, 'plainText': body},
        }
        if attachments:
            message['attachments'] = attachments
        client.begin_send(message).result()
        logger.info('Email sent: %s (%d odbiorców)', subject, len(recipients))
        return True
    except Exception as exc:
        logger.error('Email send failed: %s', exc)
        return False


def clean_recipients(values):
    """Zwraca (lista unikalnych adresów, lista błędnych adresów)."""
    emails = list(dict.fromkeys(v.strip() for v in values if v.strip()))
    invalid = []
    for e in emails:
        try:
            validate_email(e)
        except ValidationError:
            invalid.append(e)
    return emails, invalid
