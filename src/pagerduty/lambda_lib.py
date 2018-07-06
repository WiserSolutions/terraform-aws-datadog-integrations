#
# Datadog integrations lambda library
#
from __future__ import print_function
import boto3
import distutils.util
import fnmatch
import json
import logging
import os
import requests
from botocore.exceptions import ClientError


## No handler for root when run locally
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def get_config_file():
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
    return config

def get_config_env(config):
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
    return config

def get_config():
    config = get_config_file()
    logger.debug("Config before overrides: {}".format(json.dumps(config, indent=2)))
    config = get_config_env(config)
    logger.debug("Config after overrides: {}".format(json.dumps(config, indent=2)))
    return config

def get_secret(secret_name, endpoint_url, region_name):
    # TODO: add json support or leave to caller ?
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name,
        endpoint_url=endpoint_url
    )

    print("Lookup secret: {}".format(secret_name))
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("The requested secret " + secret_name + " was not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # Secret name not exists?
            print("The request was invalid due to:", e)
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            print("The request had invalid params:", e)
        else:
            print("Unknown error: ", e)
    else:
        # Decrypted secret using the associated KMS CMK
        # Depending on whether the secret was a string or binary, one of these fields will be populated
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            #print(json.dumps(json.loads(secret), indent=2))
            #print(secret)
            # Try json decode
            try:
                secret_decoded = json.loads(secret)
            except:
                secret_decoded = secret
            return secret_decoded
        else:
            binary_secret_data = get_secret_value_response['SecretBinary']
            return binary_secret_data

def get_integration_parts(s3_bucket, prefix, pattern):
    # s3 bucket, s3 path (prefix), file pattern
    # Parts: channels, service hook (name, url), Slack api token (2 parts),
    # Return: list of integration parts
    parts = []
    s3 = boto3.client('s3')
    list = s3.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)
    # TODO: Handle no objects found. Use try
    #print(list)
    for obj in list["Contents"]:
        # Pattern match on text after prefix. UNIX globbing - Could use regex
        if fnmatch.fnmatch(obj["Key"], prefix + "/" + pattern):
            print("Reading object: {}".format(obj["Key"]))
            try:
                part_result = s3.get_object(Bucket=s3_bucket, Key=obj["Key"])
                logger.debug("S3 get config: {}".format(part_result))
                part_raw = part_result["Body"].read()
                part = json.loads(part_raw)
                if 'default' in part:
                    default = part['default']
                    part.pop('default', None)
                    logger.debug("Default value: '{}'".format(default))
                    try:
                        if distutils.util.strtobool(default):
                            parts.insert(0, part)
                        else:
                            parts.append(part)
                    except ValueError:
                        parts.append(part)
                else:
                    parts.append(part)
            except ClientError as e:
                logger.warn("Reading Datadog integration segment from S3 failed: {}".format(e))
    return parts

def write_datadog_integration(datadog_keys, integration, payload):
    # Datadog: url, api_key, app_key
    # POST: Create integration: Does add, not delete or update. Can have duplicate entries
    # PUT: Create/Update integration: updates, deletes
    #print(json.dumps(payload, indent=2))
    url_base = "https://api.datadoghq.com/api/v1/integration/" + integration
    api = "?api_key=" + datadog_keys["api_key"]
    app = "&application_key=" + datadog_keys["app_key"]
    url = url_base + api + app + "&run_check=true"
    headers = {"Content-type": "application/json"}
    print("URL: {}".format(url))
    result = requests.put(url, data=json.dumps(payload), headers=headers)
    print(result)
    if result.status_code != 204:
        logger.error("Datadog {} integration update failed with status: {}".format(integration, result.status_code))
        #logger.debug("HTTP response header {}".format(json.dumps(result.headers, indent=2)))
