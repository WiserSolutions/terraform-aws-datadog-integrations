from __future__ import print_function
import boto3
import fnmatch
import json
import logging
import os
import pypd
import requests
#import slack
from botocore.exceptions import ClientError

# TODO:

# No handler for root when run locally
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
states = {}

def get_config():
    # Allow different config file to be specified
    if 'LAMBDA_CONFIG' in os.environ and len(os.getenv('LAMBDA_CONFIG')) > 0:
        config_file = os.getenv('LAMBDA_CONFIG')
        if config_file.find("s3://") == 0:
            # read from S3 or copy default to s3
            s3_bucket = config_file[5:len(config_file)].split("/")[0]
            sep = "/"
            s3_object = sep.join(config_file[5:len(config_file)].split("/")[1:])
            s3 = boto3.client('s3')
            try:
                config_result = s3.get_object(Bucket=s3_bucket, Key=s3_object)
                logger.debug("S3 get config: {}".format(config_result))
                config_raw = config_result["Body"].read()
                config = json.loads(config_raw)
            except ClientError as e:
                logger.warn("Config not found in S3: {}".format(e))
                logger.warn("Copying default config to S3")
                with open('config.json') as f:
                    config = json.load(f)
                    s3.put_object(Bucket=s3_bucket, Key=s3_object, Body=json.dumps(config, indent=2))
        else:
            logger.debug("Reading config file: {}".format(config_file))
            with open(config_file) as f:
                config = json.load(f)
    else:
        logger.debug("Reading config file: config.json")
        with open('config.json') as f:
            config = json.load(f)

    logger.debug("Config before overrides: {}".format(json.dumps(config, indent=2)))
    # Replace config data with environment data if it exists
    # Environment variables are keys uppercased
    for key in config.keys():
        if key.upper() in os.environ:
            value = os.getenv(key.upper())
            try:
                value_json = json.loads(value)
                logger.debug("Got json: {}".format(json.dumps(value_json)))
                if len(value_json.keys()) > 0:
                    config[key] = value_json
            except:
                if len(value) > 0:
                    config[key] = value
    logger.debug("Config after overrides: {}".format(json.dumps(config, indent=2)))
    return config

def get_secret(secret_name, endpoint_url, region_name):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name,
        endpoint_url=endpoint_url
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("The requested secret " + secret_name + " was not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            print("The request was invalid due to:", e)
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            print("The request had invalid params:", e)
    else:
        # Decrypted secret using the associated KMS CMK
        # Depending on whether the secret was a string or binary, one of these fields will be populated
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            #print(json.dumps(json.loads(secret), indent=2))
            #print(secret)
            return secret
        else:
            binary_secret_data = get_secret_value_response['SecretBinary']
            return binary_secret_data

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
    services = []
    s3 = boto3.client('s3')
    list = s3.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)
    # TODO: Handle no objects found
    #print(list)
    for obj in list["Contents"]:
        # Pattern match on text after prefix. UNIX globbing - Could use regex
        if fnmatch.fnmatch(obj["Key"], prefix + "/" + pattern):
            print("Reading object: {}".format(obj["Key"]))
            try:
                service_result = s3.get_object(Bucket=s3_bucket, Key=obj["Key"])
                logger.debug("S3 get config: {}".format(service_result))
                service_raw = service_result["Body"].read()
                service = json.loads(service_raw)
                services.append(service)
            except ClientError as e:
                logger.warn("Config not found in S3: {}".format(e))
                logger.warn("Copying default config to S3")
    #print("PagerDuty services: {}".format(json.dumps(services, indent=2)))
    return services

    #print(json.dumps(list, indent=2))
    #config_result = s3.get_object(Bucket=config["s3_bucket_parts"], Key=s3_object)

    #datadog_api_base = "https://api.datadoghq.com/api/v1/"
    #integration_base = datadog_api_base + "integration/"
    #slack = integration_base + "slack"

def get_schedules(config):
    # Get from DD
    # Read: curl -v "https://api.datadoghq.com/api/v1/integration/pagerduty?api_key=${api_key}&application_key=${app_key}"
    # ["schedules"]
    url_base = "https://api.datadoghq.com/api/v1/integration/pagerduty"
    api = "?api_key=" + config["datadog_api_key"]
    app = "&application_key=" + config["datadog_app_key"]
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


def write_datadog_pagerduty(config, services, schedules):
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
    print(json.dumps(data, indent=2))
    url_base = "https://api.datadoghq.com/api/v1/integration/pagerduty"
    api = "?api_key=" + config["datadog_api_key"]
    app = "&application_key=" + config["datadog_app_key"]
    url = url_base + api + app + "&run_check=true"
    headers = {"Content-type": "application/json"}
    print("URL: {}".format(url))
    #result = requests.delete(url_base + api + app)
    #print(result)
    #result = requests.post(url, data=json.dumps(data), headers=headers)
    result = requests.put(url, data=json.dumps(data), headers=headers)
    print(result)
    if result.status_code != 204:
        logger.error("Datadog Pagerduty integration update failed with status: {}".format(result.status_code))
        #logger.debug("HTTP response header {}".format(json.dumps(result.headers, indent=2)))

#
# datadog_integration_slack():
#   read, write, delete

def lambda_handler(event, context):
    global states
    config = get_config()

    # Setup logging
    log_level = getattr(logging, config["log_level"].upper(), None)
    if not isinstance(log_level, int):
        raise ValueError('Invalid log level: {}'.format(config["log_level"]))
    logger.setLevel(log_level)
    services = get_pagerduty_services(config["s3_bucket_parts"], config["path_parts"], config["parts_pattern"])
    schedules = get_schedules(config)
    #slack_webhook = get_secret(config["secret_name"], config["secret_endpoint_url"], config["aws_region"])
    #slack_hooks = get_slack_hooks(slack_webhook)
    write_datadog_pagerduty(config, services, schedules)

    return 'Done'

# Local testing
if __name__ == '__main__':
    print('Local testing')
    print(lambda_handler(None, None))
