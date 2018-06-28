from __future__ import print_function
import boto3
import fnmatch
import json
import lambda_lib
import logging
import os
import pypd
import requests
from botocore.exceptions import ClientError

# TODO:

# No handler for root when run locally
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
states = {}


#def get_s3_parts():

def get_pagerduty_services(s3_bucket, prefix, pattern):
    # s3 bucket, s3 path (prefix), file pattern
    # Parts: channels, service hook (name, url), Slack api token (2 parts),
    # Slack hook: Name & url -> secrets manager
    # Datadog api & app token (secrets manager)
    #   boto3:
    #   client = boto3.client('secretsmanager')
    #   response = client.get_secret_value(
    #        SecretId='string',
    #        VersionStage='string'
    #    )
    # IAM permissions to read:
    #   secretsmanager:ListSecrets - to navigate to the secret you want to retrieve
    #   secretsmanager:DescribeSecret - to retrieve the non-encrypted parts of the secret
    #   secretsmanager:GetSecretValue - to retrieve the encrypted part of the secret
    #   kms:Decrypt - Only required if you used a custom KMS CMK to encrypt your secret
    # Return: list of channel names
    services = lambda_lib.get_integration_parts(s3_bucket, prefix, pattern)
    #print("PagerDuty services: {}".format(json.dumps(services, indent=2)))
    return services

def get_schedules(datadog_keys):
    # Get from DD
    # Read: curl -v "https://api.datadoghq.com/api/v1/integration/pagerduty?api_key=${api_key}&application_key=${app_key}"
    # ["schedules"]
    url_base = "https://api.datadoghq.com/api/v1/integration/pagerduty"
    api = "?api_key=" + datadog_keys["api_key"]
    app = "&application_key=" + datadog_keys["app_key"]
    url = url_base + api + app + "&run_check=true"
    print("URL: {}".format(url))
    #result = requests.delete(url_base + api + app)
    #print(result)
    #result = requests.post(url, data=json.dumps(data), headers=headers)
    result = requests.get(url)
    #print(result)
    data = result.json()
    #print("Results: {}".format(json.dumps(data, indent=2)))
    return data["schedules"]

def write_datadog_pagerduty(config, datadog_keys, services, schedules):
    # Datadog: url, api_key, app_key
    # POST: Create integration: Does add, not delete or update. Can have duplicate entries
    # PUT: Create/Update integration: updates, deletes
    # TODO: need RO pagerduty api token: Get from Igor or create new
    #   read from datadog and see what's usable: schedules, subdomain
    data = {}
    data["services"] = services
    data["subdomain"] = config["pagerduty_subdomain"]
    data["schedules"] = schedules
    data["api_token"] = config["pagerduty_ro_key"]
    #print(json.dumps(data, indent=2))
    lambda_lib.write_datadog_integration(datadog_keys, 'pagerduty', data)

def lambda_handler(event, context):
    global states
    config = lambda_lib.get_config()

    # Setup logging
    log_level = getattr(logging, config["log_level"].upper(), None)
    if not isinstance(log_level, int):
        raise ValueError('Invalid log level: {}'.format(config["log_level"]))
    logger.setLevel(log_level)
    # TODO: read event, if DeletedObject remove PagerDuty service
    logger.debug("Event: {}".format(json.dumps(event, indent=2)))
    logger.debug("Context: {}".format(context))

    services = get_pagerduty_services(config["s3_bucket_parts"], config["path_parts"], config["parts_pattern"])
    # Secrets: DD api, DD app, pagerduty RO
    datadog_keys = lambda_lib.get_secret(config["secrets"]["datadog_api"], config["secret_endpoint_url"], config["aws_region"])
    config["pagerduty_ro_key"] = lambda_lib.get_secret(config["secrets"]["pagerduty_ro"], config["secret_endpoint_url"], config["aws_region"])
    schedules = get_schedules(datadog_keys)
    write_datadog_pagerduty(config, datadog_keys, services, schedules)

    return 'Done'

# Local testing
if __name__ == '__main__':
    print('Local testing')
    print(lambda_handler(None, None))
