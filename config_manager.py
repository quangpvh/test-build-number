import argparse
import requests
import io

from oauth2client.service_account import ServiceAccountCredentials
import json

import os

PROJECT_ID = os.getenv("PROJECT_ID")
FILE_DIR = os.getenv("CREDENTIALS")
PLATFORM_APP = os.getenv("PLATFORM_APP")
VERSION_APP = os.getenv("VERSION_APP")


contentData = None
with open(FILE_DIR, 'r') as f:
    contentData = f.read()

CREDENTIALS = json.loads(contentData)


BASE_URL = "https://firebaseremoteconfig.googleapis.com"
REMOTE_CONFIG_ENDPOINT = "v1/projects/" + PROJECT_ID + "/remoteConfig"
REMOTE_CONFIG_URL = BASE_URL + "/" + REMOTE_CONFIG_ENDPOINT
SCOPES = ["https://www.googleapis.com/auth/firebase.remoteconfig"]

# [START retrieve_access_token]
def _get_access_token():
    """Retrieve a valid access token that can be used to authorize requests.
    :return: Access token.
    """
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(CREDENTIALS, SCOPES)
    access_token_info = credentials.get_access_token()
    return access_token_info.access_token


# [END retrieve_access_token]


def _get(save=False):
    """Retrieve the current Firebase Remote Config template from server.
    Retrieve the current Firebase Remote Config template from server and store it
    locally. 
    """
    access_token = _get_access_token()
    print(access_token)
    headers = {"Authorization": "Bearer " + access_token}
    resp = requests.get(REMOTE_CONFIG_URL, headers=headers)
    print(resp.json())
    print(resp.headers["ETag"])
    print(resp.status_code)

    if save != False and resp.status_code == 200:
        with io.open("config.json", "wb") as f:
            f.write(resp.text.encode("utf-8"))

        print("Retrieved template has been written to config.json")
    return resp.json(), resp.headers["ETag"]


def _listVersions():
    """Print the last 5 Remote Config version's metadata."""
    headers = {"Authorization": "Bearer " + _get_access_token()}
    resp = requests.get(REMOTE_CONFIG_URL + ":listVersions?pageSize=5", headers=headers)

    if resp.status_code == 200:
        print("Versions:")
        print(resp.text)
    else:
        print("Request to print template versions failed.")
        print(resp.text)


def _rollback(version):
    """Roll back to an available version of Firebase Remote Config template.
    :param version: The version of the template to roll back to.
    """
    headers = {"Authorization": "Bearer " + _get_access_token()}

    json = {"version_number": version}
    resp = requests.post(REMOTE_CONFIG_URL + ":rollback", headers=headers, json=json)

    if resp.status_code == 200:
        print("Rolled back to version: " + version)
        print(resp.text)
        print("ETag from server: {}".format(resp.headers["ETag"]))
    else:
        print("Request to roll back to version " + version + " failed.")
        print(resp.text)


def _publish():
    """Publish local template to Firebase server.
    Args:
      etag: ETag for safe (avoid race conditions) template updates.
          * can be used to force template replacement.
    """
    current_data , etag = _get()
    print("data = ", current_data)
    headers = {
        "Authorization": "Bearer " + _get_access_token(),
        "Content-Type": "application/json; UTF-8",
        "If-Match": etag,
    }

    content = None
    if current_data is None or len(current_data) == 0:
        content = {
            "conditions": [{
              "name": "device_lang",
              "expression": "device.country in ['vn', 'jp']"
            }],
            "parameters": {
              "app_version_android": {
                "defaultValue": {
                  "value": None
                },
                "conditionalValues": {
                  "device_lang": {
                    "value": None
                  }
                },
                "description": "App version android"
              },
              "app_version_ios": {
                "defaultValue": {
                  "value": None
                },
                "conditionalValues": {
                  "device_lang": {
                    "value": None
                  }
                },
                "description": "App version ios"
              },
            }
        }
        
    if PLATFORM_APP == "ios":
        if current_data['app_version_ios'] != None:
          current_data['app_version_ios']['conditionalValues']['device_lang']['value'] = VERSION_APP
        else:
          current_data['app_version_ios']['conditionalValues']['device_lang']['value'] = VERSION_APP

    else:
        if current_data['app_version_android'] != None:
          current_data['app_version_android']['conditionalValues']['device_lang']['value'] = VERSION_APP
        else:
          current_data['app_version_android']['conditionalValues']['device_lang']['value'] = VERSION_APP            
        

    content = current_data
    resp = requests.put(
        REMOTE_CONFIG_URL, data=json.dumps(content), headers=headers
    )
    if resp.status_code == 200:
        print("Template has been published.")
        print("ETag from server: {}".format(resp.headers["ETag"]))
    else:
        print("Unable to publish template.")
        print(resp.text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action")
    parser.add_argument("--etag")
    parser.add_argument("--version")
    args = parser.parse_args()

    if args.action and args.action == "get":
        _get()
    elif args.action and args.action == "publish":
        _publish()
    elif args.action and args.action == "versions":
        _listVersions()
    elif args.action and args.action == "rollback" and args.version:
        _rollback(args.version)
    else:
        print(
            """Invalid command. Please use one of the following commands:
python configure.py --action=get
python configure.py --action=publish
python configure.py --action=versions
python configure.py --action=rollback --version=<TEMPLATE_VERSION_NUMBER>"""
        )


if __name__ == "__main__":
    main()