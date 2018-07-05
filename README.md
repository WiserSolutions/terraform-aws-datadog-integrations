# terraform-datadog-integrations

The Datadog API only supports fully defining and deleting an integration.
This creates an issue when the desire is to manage by service NOT a global
config. To solve this, Terraform for each service will write the service's
settings to S3, this will a trigger a lambda to combine the information from
all the services and update the Datadog integration

Lambda (per integration or 1 for all integrations).
Submodules for services to call to generate data and write to S3

Will need to maintain last config uploaded to be able to tell what is managed
and what can be deleted. Don't remove manually created items

Manually add current config pieces to S3 paths.
Read S3 path and file pattern, build data structure.
Read old data structure and compare with new.
Log what is being removed and/or added

Lambdas:

PagerDuty:
Read S3 path and file pattern, build data structure
Build data structure, update Datadog

Slack:
Read S3 path and file pattern, build data structure
Build data structure, update Datadog
Add/remove Slack channels
On add: set purpose, add bots (pagerduty)
