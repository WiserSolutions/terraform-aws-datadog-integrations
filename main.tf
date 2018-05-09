
/*
create s3 bucket: permissions, encryption required
manage lambdas:
  pagerduty: update Datadog integration
  slack: update Datadog integration, ensure channel exist or remove if no longer in config, set purpose, add bots
  Setup s3 triggers

/**/

# IAM permissions
# Cloudwatch: logging
# S3: list & read objects
#   ListObjects
#   GetObject
# Secrets Manager: read secrets:
#   secretsmanager:ListSecrets – to navigate to the secret you want to retrieve
#   secretsmanager:DescribeSecret — to retrieve the non-encrypted parts of the secret
#   secretsmanager:GetSecretValue – to retrieve the encrypted part of the secret
#   kms:Decrypt – Only required if you used a custom KMS CMK to encrypt your secret

/*
resource "aws_s3_bucket" "monitoring" {
  count  = "${var.states_s3_bucket_id == "" ? 1 : 0}"
  bucket = "wiser-${var.environment}-monitoring"
  acl    = "private"

  tags {
    Environment = "${var.environment}"
    Name        = "wiser-${var.environment}-monitoring"
    Terraform   = true
  }
}
/**/

module "lambda_pagerduty" {
  source            = "./modules/lambda"
  environment       = "one"
  lambda_desc       = "Datadog Pagerduty Integration"
  lambda_env_vars   = "${var.lambda_pagerduty_env_vars}"
  lambda_handler    = "datadog-pagerduty-integration.lambda_handler"
  lambda_name       = "datadog_pagerduty"
  s3_bucket         = "wiser-one-ci"
  source_dir        = "pagerduty"
}

module "lambda_slack" {
  source            = "./modules/lambda"
  environment       = "one"
  lambda_desc       = "Datadog Slack Integration"
  lambda_env_vars   = "${var.lambda_slack_env_vars}"
  lambda_handler    = "datadog-slack-integration.lambda_handler"
  lambda_name       = "datadog_slack"
  s3_bucket         = "wiser-one-ci"
  source_dir        = "slack"
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = "${module.lambda_pagerduty.s3_bucket_id}"

  lambda_function {
    lambda_function_arn = "${module.lambda_pagerduty.lambda_arn}"
    events              = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
    filter_prefix       = "datadog/integration/pagerduty/"
    filter_suffix       = ".json"
  }
  lambda_function {
    lambda_function_arn = "${module.lambda_slack.lambda_arn}"
    events              = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
    filter_prefix       = "datadog/integration/slack/"
    filter_suffix       = ".json"
  }
}
