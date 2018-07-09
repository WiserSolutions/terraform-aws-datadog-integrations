module "service" {
  source       = "../../modules/pagerduty"
  service_key  = ""
  service_name = "testing_disable_tf"
  s3_bucket    = "wiser-infra-automation"
}
