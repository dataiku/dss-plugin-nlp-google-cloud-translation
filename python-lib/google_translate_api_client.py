# -*- coding: utf-8 -*-
"""Module with utility functions to call the Google translation API"""

import logging
import json

from google.cloud import translate_v2 as translate
from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.oauth2 import service_account


# ==============================================================================
# CONSTANT DEFINITION
# ==============================================================================


API_EXCEPTIONS = (GoogleAPICallError, RetryError)


# ==============================================================================
# CLASS AND FUNCTION DEFINITION
# ==============================================================================


def get_client(gcp_service_account_key=None):
    """
    Get a translate API client from the service account key.
    """
    if gcp_service_account_key is None or gcp_service_account_key == "":
        return translate.Client()
    try:
        credentials = json.loads(gcp_service_account_key)
    except (ValueError, TypeError) as e:
        logging.error(e)
        raise ValueError("GCP service account key is not valid JSON")
    credentials = service_account.Credentials.from_service_account_info(credentials)
    logging.info("Credentials loaded")
    client = translate.Client(credentials=credentials)
    return client
