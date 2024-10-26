import json
import os
import requests
from requests import Response

STATUS_SUCCESS = 200


def is_response_successful(response: requests.Response) -> bool:
    return response.status_code == STATUS_SUCCESS

def get_response(path) -> Response:
    response = requests.get(os.environ['SERVER_URL'] + path,
                                headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
    return response

def get_json_response(path, error_message="Error while response") -> json:
    response = get_response(path)
    if not is_response_successful(response):
        print(error_message)
        return {}
    return response.json()