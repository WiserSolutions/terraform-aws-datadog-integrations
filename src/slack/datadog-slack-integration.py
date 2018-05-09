from __future__ import print_function
import boto3
import fnmatch
import json
import logging
import os
import requests
#import slack
from botocore.exceptions import ClientError

# TODO:
#   ensure channel exist and are setup in Slack

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

def get_slack_channels(s3_bucket, prefix, pattern):
    # Return: list of channel names
    channels = []
    s3 = boto3.client('s3')
    list = s3.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)
    #print(list)
    for obj in list["Contents"]:
        # Pattern match on text after prefix. UNIX globbing - Could use regex
        if fnmatch.fnmatch(obj["Key"], prefix + "/" + pattern):
            print("Reading object: {}".format(obj["Key"]))
            try:
                # TODO: support channel and service_hook
                channel_result = s3.get_object(Bucket=s3_bucket, Key=obj["Key"])
                logger.debug("S3 get config: {}".format(channel_result))
                channel_raw = channel_result["Body"].read()
                channel = json.loads(channel_raw)
                if not "transfer_all_user_comments" in channel:
                    channel["transfer_all_user_comments"] = "false"
                if not "account" in channel:
                    channel["account"] = "Main_Account"
                channels.append(channel)
            except ClientError as e:
                logger.warn("Config not found in S3: {}".format(e))
                logger.warn("Copying default config to S3")
    return channels

###
### Slack channel management
###
# TODO:
#   future - Replace with terraform slack provider
#   rework so all API calls & error handling goes to a single routine
#   Copy all slack code to own file for testing
#   Change print to logger

# channel max name length ?
# mon-xxxx- = 9
# Lookup pagerduty_slack_bot user id

#def slack_api(method, api, data):

def get_channels():
    global arg_token
    global url_base
    url = url_base + "channels.list?" + arg_token
    result = requests.get(url)
    data = result.json()
    return data["channels"]

def get_users():
    global arg_token
    global url_base
    url = url_base + "users.list?" + arg_token
    result = requests.get(url)
    data = result.json()
    return data["members"]

def get_channel_by_name(channels, name):
    for channel in channels:
        if channel["name"] == name:
            return channel

def get_channel_id_by_name(channels, name):
    id = ""
    for channel in channels:
        if channel["name"] == name:
            id = channel["id"]
    return id

def get_user_id_by_name(users, name):
    id = ""
    for user in users:
        if user["name"] == name:
            id = user["id"]
    return id

def add_channel_user(channel_id, user_id):
    #   https://api.slack.com/methods/channels.invite
    global arg_token
    global url_base
    url = url_base + "channels.invite?" + arg_token + "&channel=" + channel_id + "&user=" + user_id
    result = requests.post(url)
    print("Add usr results {}".format(result))

def set_channel_purpose(channel_id, purpose):
    print("\tAdd purpose...")
    #purpose = "Alerts/Notifications for " + repo + " in " + env
    global arg_token
    global url_base
    p = urllib.quote_plus(purpose)
    url = url_base + "channels.setPurpose?" + arg_token + "&channel=" + channel_id + "&purpose=" + p + "&pretty=1"
    print("\turl: {}".format(url))
    result = requests.post(url)
    print("\tresult status: {}".format(result.status_code))

def create_channel(name):
    global arg_token
    global url_base
    channel_id = ""
    print("Creating channel: {}".format(name))
    url = url_base + "channels.create?" + arg_token + "&name=" + name + "&validate=true&pretty=1"
    print("\turl: {}".format(url))
    result = requests.post(url)
    print("\tresult status: {}".format(result.status_code))
    print(result)
    data = result.json()
    print(data)
    if "ok" in data:
        channel_id = result.json() ["channel"]["id"]
    return channel_id

def channel_join(name):
    # Will create channel if it does not exist
    global arg_token
    global url_base
    channel_id = ""
    url = url_base + "channels.join?" + arg_token + "&name=" + name + "&pretty=1"
    print("\turl: {}".format(url))
    result = requests.post(url)
    print("\tresult status: {}".format(result.status_code))
    # Returns channel object (same as info gets)
    data = result.json()
    #print(data)
    if "ok" in data:
        #channel_id = data["channel"]["id"]
        return data["channel"]

def channel_leave(id):
    global arg_token
    global url_base
    url = url_base + "channels.leave?" + arg_token + "&channel=" + id + "&pretty=1"
    print("\turl: {}".format(url))
    result = requests.post(url)
    print("\tresult status: {}".format(result.status_code))

def channel_info(id):
    # Get from channels list
    global arg_token
    global url_base
    url = url_base + "channels.info?" + arg_token + "&channel=" + id + "&pretty=1"
    print("\turl: {}".format(url))
    result = requests.get(url)
    print("\tresult status: {}".format(result.status_code))
    return result.json()

def manage_channels(existing, managed):
    # FIX: existing is list of channel dicts, managed is list
    slack_bot = "pagerduty_slack_bot"
    users = get_users()
    pagerduty_id = get_user_id_by_name(users, slack_bot)
    for name in managed:
        channel_info = channel_join(name)
        #if name in existing: # What should compare/lookup be?
        #    channel_id = get_channel_id_by_name(existing, name)
        #    # channel_id = channel_join(name)
        #else:
        #    channel_id = create_channel(name)

        #channel_info = get_channel_by_name(name) # if was existing
        purpose_old  = channel_info["purpose"]["value"]
        member_ids   = channel_info["members"]
        # Get purpose, set if not current
        # Parse name to get service and env
        purpose_new = "Alerts/Notifications for {} in {}".format(service, env)
        if purpose_old != purpose_new:
            set_channel_purpose(channel_info["id"], purpose_new)
        if pagerduty_id not in member_ids:
            add_channel_user(channel_info["id"], pagerduty_id)
        channel_leave(channel_info["id"])


def update_slack_channels(channels):
    # Build library
    # Ensure channel exist
    # Ensure current purpose is set
    # Invite pagerduty bot, other bots?
    # Remove channels no longer used. Need to track changes or by pattern (assume certain pattern is fully managed)
    global arg_token
    global url_base
    arg_token = "token=" + config["slack_token"]
    url_base = "https://slack.com/api/"

    channels_exist = get_channels()
    print("# Channels: {}".format(len(channels)))
    print("# Users: {}".format(len(users)))
    print("Pagerduty ID: {}".format(pagerduty_id))
    #manage_channels(channels_exist, channels)


###
### Datadog integration
###

def get_slack_hooks(url):
    hooks = []
    hooks.append({
        "url"     : url,
        "account" : "Main_Account"
    })
    return hooks

def write_datadog_slack(config, channels, service_hooks):
    # Datadog: url, api_key, app_key
    # POST: Create integration: Does add, not delete or update. Can have duplicate entries
    # PUT: Create/Update integration: updates, deletes
    data = {}
    data["channels"]      = channels
    data["service_hooks"] = service_hooks
    #print(json.dumps(data, indent=2))
    url_base = "https://api.datadoghq.com/api/v1/integration/slack"
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
        logger.error("Datadog Slack integration update failed with status: {}".format(result.status_code))
        #logger.debug("HTTP response header {}".format(json.dumps(result.headers, indent=2)))

def lambda_handler(event, context):
    global states
    config = get_config()

    # Setup logging
    log_level = getattr(logging, config["log_level"].upper(), None)
    if not isinstance(log_level, int):
        raise ValueError('Invalid log level: {}'.format(config["log_level"]))
    logger.setLevel(log_level)
    # TODO: read event, if DeletedObject archive/remove Slack channel
    logger.debug("Event: {}".format(json.dumps(event, indent=2)))
    logger.debug("Context: {}".format(json.dumps(context, indent=2)))
    channels = get_slack_channels(config["s3_bucket_parts"], config["path_parts"], config["parts_pattern"])
    slack_webhook = get_secret(config["secret_name"], config["secret_endpoint_url"], config["aws_region"])
    slack_hooks = get_slack_hooks(slack_webhook)
    #update_slack_channels(channels)
    write_datadog_slack(config, channels, slack_hooks)

    return 'Done'

# Local testing
if __name__ == '__main__':
    print('Local testing')
    print(lambda_handler(None, None))
