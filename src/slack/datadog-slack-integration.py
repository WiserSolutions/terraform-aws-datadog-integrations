from __future__ import print_function
import boto3
import fnmatch
import json
import lambda_lib
import logging
import os
import requests
# Create library: import slack
from botocore.exceptions import ClientError

# TODO:
#   ensure channel exist and are setup in Slack
#   Read lambda event
#       Object key/path:
#           ["Records"][]["s3"]["object"]["key"]
#       Event ObjectCreated:Put
#           ["Records"][]["eventName"]

# No handler for root when run locally
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
states = {}

def get_slack_channels(s3_bucket, prefix, pattern):
    # Return: list of channel names
    channels = lambda_lib.get_integration_parts(s3_bucket, prefix, pattern)
    for channel in channels:
        if not "transfer_all_user_comments" in channel:
            channel["transfer_all_user_comments"] = "false"
        if not "account" in channel:
            channel["account"] = "Main_Account"
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
    # Define purpose = "Alerts/Notifications for " + repo + " in " + env
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
    # Define channel_id = ""
    url = url_base + "channels.join?" + arg_token + "&name=" + name + "&pretty=1"
    print("\turl: {}".format(url))
    result = requests.post(url)
    print("\tresult status: {}".format(result.status_code))
    # Returns channel object (same as info gets)
    data = result.json()
    #print(data)
    if "ok" in data:
        # Get channel id: channel_id = data["channel"]["id"]
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

    # Get channels_exist = get_channels()
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
    data = {}
    data["channels"]      = channels
    data["service_hooks"] = service_hooks
    #print(json.dumps(data, indent=2))
    lambda_lib.write_datadog_integration(config, 'slack', data)

def lambda_handler(event, context):
    global states
    config = lambda_lib.get_config()

    # Setup logging
    log_level = getattr(logging, config["log_level"].upper(), None)
    if not isinstance(log_level, int):
        raise ValueError('Invalid log level: {}'.format(config["log_level"]))
    logger.setLevel(log_level)
    # TODO: read event, if DeletedObject archive/remove Slack channel
    logger.debug("Event: {}".format(json.dumps(event, indent=2)))
    logger.debug("Context: {}".format(context))
    channels = get_slack_channels(config["s3_bucket_parts"], config["path_parts"], config["parts_pattern"])
    # Secrets: DD api, DD app, slack webhook
    datadog_keys = lambda_lib.get_secret(config["secrets"]["datadog_api"], config["secret_endpoint_url"], config["aws_region"])
    slack_webhook = lambda_lib.get_secret(config["secrets"]["slack_webhook"], config["secret_endpoint_url"], config["aws_region"])
    slack_hooks = get_slack_hooks(slack_webhook)
    #update_slack_channels(channels)
    write_datadog_slack(datadog_keys, channels, slack_hooks)

    return 'Done'

# Local testing
if __name__ == '__main__':
    print('Local testing')
    print(lambda_handler(None, None))
