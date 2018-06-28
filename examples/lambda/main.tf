module "integration_lambda" {
  source                    = "../.."
  environment               = "${var.environment}"
  lambda_pagerduty_env_vars = "${var.lambda_pagerduty_env_vars}"
  lambda_slack_env_vars     = "${var.lambda_slack_env_vars}"
  s3_bucket                 = "${var.s3_bucket}"
}
