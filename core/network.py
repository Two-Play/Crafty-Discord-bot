"""
This module contains functions for sending HTTP requests and handling responses.
"""

import json
import os
import requests
from requests import Response

from core.constants import STATUS_SUCCESS


def is_response_successful(response: requests.Response) -> bool:
    """
    Check if the HTTP response was successful.

    Args:
        response (requests.Response): The HTTP response object.

    Returns:
        bool: True if the response status code is 200, False otherwise.
    """
    return response.status_code == STATUS_SUCCESS


def get_response(path: str, verify: bool = False, timeout: int = 6) -> Response:
    """
    Send a GET request to the specified path and return the response.

    Args:
        path (str): The URL path to send the request to.
        verify (bool, optional): Whether to verify the server's TLS certificate. Defaults to False.
        timeout (int, optional): The timeout for the request in seconds. Defaults to 6.

    Returns:
        requests.Response: The HTTP response object.
    """
    response = requests.get(
        os.environ['SERVER_URL'] + path,
        headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']},
        verify=verify,
        timeout=timeout
    )
    return response


def get_json_response(path: str, error_message: str = "Error while response") -> json:
    """
    Send a GET request to the specified path and return the response as JSON.

    Args:
        path (str): The URL path to send the request to.
        error_message (str, optional): The error message to print if the response is
        not successful. Defaults to "Error while response".

    Returns:
        dict: The JSON response as a dictionary. Returns an empty dictionary
        if the response is not successful.
    """
    response = get_response(path)
    if not is_response_successful(response):
        print(error_message)
        return {}
    return response.json()
