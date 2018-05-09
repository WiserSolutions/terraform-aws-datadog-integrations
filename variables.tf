variable "lambda_pagerduty_env_vars" {
  description = "Environment variable to provide to PagerDuty lambda"
  type        = "map"
  default     = {}
}

variable "lambda_slack_env_vars" {
  description = "Environment variable to provide to Slack lambda"
  type        = "map"
  default     = {}
}
