# NOTE: this script was designed using the v1.1
# version of the OMF specification, as outlined here:
# http://omf-docs.osisoft.com/en/v1.1
# *************************************************************************************

# ************************************************************************
# Import necessary packages
# ************************************************************************

import configparser
import json
import time
import datetime
import platform
import socket
import gzip
import random
import requests
import traceback
import base64

app_config = {}


def getToken():
    # Gets the oken for the omfsendpoint
    global app_config

    if(app_config.EDS):
        return
    if(app_config.PI):
        return

    if ((app_config.__expiration - time.time()) > 5 * 60):
        return app_config.__token

    # we can't short circuit it, so we must go retreive it.

    discoveryUrl = requests.get(
        app_config.resourceBase + "/identity/.well-known/openid-configuration",
        headers={"Accept": "application/json"},
        verify=app_config.VERIFY_SSL)

    if discoveryUrl.status_code < 200 or discoveryUrl.status_code >= 300:
        discoveryUrl.close()
        print("Failed to get access token endpoint from discovery URL: {status}:{reason}".
              format(status=discoveryUrl.status_code, reason=discoveryUrl.text))
        raise ValueError

    tokenEndpoint = json.loads(discoveryUrl.content)["token_endpoint"]

    tokenInformation = requests.post(
        tokenEndpoint,
        data={"client_id": app_config.Id,
              "client_secret": app_config.Secret,
              "grant_type": "client_credentials"},
        verify=app_config.VERIFY_SSL)

    token = json.loads(tokenInformation.content)

    if token is None:
        raise Exception("Failed to retrieve Token")

    app_config.__expiration = float(token['expires_in']) + time.time()
    app_config.__token = token['access_token']
    return app_config.__token


def send_omf_message_to_endpoint(message_type, msg_body, action='create'):
    # Sends the request out to the preconfigured endpoint..

    global app_config
    # Compress json omf payload, if specified
    # msg_body = json.dumps(message_omf_json)

    msg_headers = getHeaders(message_type, action)
    response = {}

    # Assemble headers
    if app_config.PI:
        response = requests.post(
            app_config.omfEndPoint,
            headers=msg_headers,
            data=msg_body,
            verify=app_config.VERIFY_SSL,
            timeout=app_config.WEB_REQUEST_TIMEOUT_SECONDS,
            auth=(app_config.Id, app_config.Secret)
        )
    else:
        response = requests.post(
            app_config.omfEndPoint,
            headers=msg_headers,
            data=msg_body,
            verify=app_config.VERIFY_SSL,
            timeout=app_config.WEB_REQUEST_TIMEOUT_SECONDS
        )

    # response code in 200s if the request was successful!
    if response.status_code < 200 or response.status_code >= 300:
        print(msg_headers)
        response.close()
        print('Response from was bad.  "{0}" message: {1} {2}.  Message holdings: {3}'.format(
            message_type, response.status_code, response.text, msg_body))
        print()
        raise Exception("OMF message was unsuccessful, {message_type}. {status}:{reason}".format(
            message_type=message_type, status=response.status_code, reason=response.text))


def getHeaders(message_type="", action=""):
    global app_config

    # Assemble headers
    if app_config.OCS:
        msg_headers = {
            "Authorization": "Bearer %s" % getToken(),
            'messagetype': message_type,
            'action': action,
            'messageformat': 'JSON',
            'omfversion': app_config.omfVersion
        }
    elif app_config.EDS:
        msg_headers = {
            'messagetype': message_type,
            'action': action,
            'messageformat': 'JSON',
            'omfversion': app_config.omfVersion
        }
    else:
        msg_headers = {
            "x-requested-with": "xmlhttprequest",
            'messagetype': message_type,
            'action': action,
            'messageformat': 'JSON',
            'omfversion': app_config.omfVersion
        }
    return msg_headers


def checkValueGone(url):
    # Sends the request out to the preconfigured endpoint..

    global app_config

    # Assemble headers
    msg_headers = getHeaders()

    # Send the request, and collect the response
    if app_config.PI:
        response = requests.get(
            url,
            headers=msg_headers,
            verify=app_config.VERIFY_SSL,
            timeout=app_config.WEB_REQUEST_TIMEOUT_SECONDS,
            auth=(app_config.Id, app_config.Secret)
        )
    else:
        response = requests.get(
            url,
            headers=msg_headers,
            verify=app_config.VERIFY_SSL,
            timeout=app_config.WEB_REQUEST_TIMEOUT_SECONDS,
        )

    # response code in 200s if the request was successful!
    if response.status_code >= 200 and response.status_code < 300:
        response.close()
        print('Value found.  This is unexpected.  "{0}"'.format(
            response.status_code))
        print()
        opId = response.headers["Operation-Id"]
        status = response.status_code
        reason = response.text
        url = response.url
        error = f"  {status}:{reason}.  URL {url}  OperationId {opId}"
        raise Exception(f"Check message was failed. {error}")
    return response.text


def checkValue(url):
    # Sends the request out to the preconfigured endpoint..

    global app_config

    # Assemble headers
    msg_headers = getHeaders()

    # Send the request, and collect the response
    if app_config.PI:
        response = requests.get(
            url,
            headers=msg_headers,
            verify=app_config.VERIFY_SSL,
            timeout=app_config.WEB_REQUEST_TIMEOUT_SECONDS,
            auth=(app_config.Id, app_config.Secret)
        )
    else:
        response = requests.get(
            url,
            headers=msg_headers,
            verify=app_config.VERIFY_SSL,
            timeout=app_config.WEB_REQUEST_TIMEOUT_SECONDS,
        )

    # response code in 200s if the request was successful!
    if response.status_code < 200 or response.status_code >= 300:
        response.close()
        print('Response from endpoint was bad.  "{0}"'.format(
            response.status_code))
        print()
        opId = response.headers["Operation-Id"]
        status = response.status_code
        reason = response.text
        url = response.url
        error = f"  {status}:{reason}.  URL {url}  OperationId {opId}"
        raise Exception(f"OMF message was unsuccessful. {error}")
    return response.text


def getCurrentTime():
    # Returns the current time
    return datetime.datetime.utcnow().isoformat() + 'Z'


def checkDeletes():
    global app_config


def checkSends(lastVal):
    global app_config


def supressError(sdsCall):
    # easily call a function and not have to wrap it individually for failure
    try:
        sdsCall()
    except Exception as e:
        print(("Encountered Error: {error}".format(error=e)))


def getConfig(section, field):
    # Reads the config file for the field specified
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config.has_option(section, field) and config.get(section, field) or ""


def getAppConfig():
    global app_config
    app_config = {}
    app_config['destinationPI'] = getConfig('Destination', 'PI')
    app_config['destinationOCS'] = getConfig('Destination', 'OCS')
    app_config['destinationEDS'] = getConfig('Destination', 'EDS')
    app_config['omfURL'] = getConfig('Access', 'omfURL')
    app_config['id'] = getConfig('Credentials', 'id')
    app_config['password'] = getConfig('Credentials', 'password')
    app_config['version'] = getConfig('Configurations', 'omfVersion')
    app_config['compression'] = getConfig('Configurations', 'compression')
    timeout = getConfig('Configurations', 'WEB_REQUEST_TIMEOUT_SECONDS')
    verify = getConfig('Configurations', 'VERIFY_SSL')

    if not timeout:
        timeout = 30
    app_config['timeout'] = timeout

    if verify == "False" or verify == "false"or verify == "FALSE":
        verify = False
    else:
        verify = True
    app_config['verify'] = verify

    return app_config


def main(test=False):
    # Main program.  Seperated out so that we can add a test function and call this easily
    global app_config
    success = True
    try:
        getAppConfig()

        with open("type.json") as myfile:
            typeData = "".join(line.rstrip() for line in myfile)
            send_omf_message_to_endpoint("type", typeData)

        with open("container.json") as myfile:
            containerData = "".join(line.rstrip() for line in myfile)
            send_omf_message_to_endpoint("container", containerData)

        with open("data.json") as myfile:
            dataData = "".join(line.rstrip() for line in myfile)
            send_omf_message_to_endpoint("data", dataData)

    except Exception as ex:
        print(("Encountered Error: {error}".format(error=ex)))
        print
        traceback.print_exc()
        print
        success = False
        raise ex
    finally:
        print('Deletes')


main()
print("done")

# Straightforward test to make sure program is working without an error in program.  Can run it yourself with pytest program.py


def test_main():
    # Tests to make sure the sample runs as expected
    main(True)