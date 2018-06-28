variable "environment" {
  description = "Deployment environment"
  default     = "infra"
}

variable "lambda_pagerduty_env_vars" {
  description = "Environment variables to provide to PagerDuty lambda"
  type        = "map"

  default = {
    "ENVIRONMENT"         = "infra"
    "LOG_LEVEL"           = "DEBUG"
    "PAGERDUTY_SUBDOMAIN" = "wiser"
    "S3_BUCKET_PARTS"     = "wiser-infra-automation"
  }
}

variable "lambda_slack_env_vars" {
  description = "Environment variables to provide to Slack lambda"
  type        = "map"

  default = {
    "ENVIRONMENT"     = "infra"
    "LOG_LEVEL"       = "DEBUG"
    "S3_BUCKET_PARTS" = "wiser-infra-automation"
    "SLACK_TOKEN"     = ""
  }
}

variable "s3_bucket" {
  description = "S3 bucket for Datadog integration parts"
  default     = "wiser-infra-automation"
}
