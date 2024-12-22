import json
import logging
import os
import requests
from requests import Response
from enum import Enum

from core.constants import STATUS_SUCCESS

logger = logging.getLogger('CraftyDiscordBot')


class HttpMethod(Enum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'
    PATCH = 'PATCH'

def is_response_successful(response: requests.Response) -> bool:
    """
    Check if the HTTP response was successful.

    Args:
        response (requests.Response): The HTTP response object.

    Returns:
        bool: True if the response status code is 200, False otherwise.
    """
    return response.status_code == STATUS_SUCCESS

def send_request(path: str, verify: bool = False, timeout: int = 6, data: dict = None, method: HttpMethod = HttpMethod.GET) -> Response:
    """
    Send an HTTP request with the specified method to the given path and return the response.

    Args:
        method (HttpMethod, optional): The HTTP method to use. Defaults to HttpMethod.GET.
        path (str): The URL path to send the request to.
        verify (bool, optional): Whether to verify the server's TLS certificate. Defaults to False.
        timeout (int, optional): The timeout for the request in seconds. Defaults to 6.
        data (dict, optional): The data to send in the request body (for POST, PUT, etc.). Defaults to None.

    Returns:
        requests.Response: The HTTP response object.
    """
    url = os.environ['SERVER_URL'] + path
    headers = {'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}
    try:
        response = requests.request(method.value, url, headers=headers, verify=verify, timeout=timeout, json=data)
        return response
    except requests.RequestException as e:
        logger.debug(f"Request failed: {e}")
        return Response()

def get_json_response(path: str, error_message: str = "Error while response", method: HttpMethod = HttpMethod.GET, data: dict = None) -> json:
    """
    Send an HTTP request with the specified method to the given path and return the response as JSON.

    Args:
        method (HttpMethod, optional): The HTTP method to use. Defaults to HttpMethod.GET.
        path (str): The URL path to send the request to.
        error_message (str, optional): The error message to print if the response is not successful. Defaults to "Error while response".
        data (dict, optional): The data to send in the request body (for POST, PUT, etc.). Defaults to None.

    Returns:
        dict: The JSON response as a dictionary. Returns an empty dictionary if the response is not successful.
    """
    response = send_request(path, method=method, data=data)
    if not is_response_successful(response):
        logger.debug(error_message)
        return {}
    return response.json()