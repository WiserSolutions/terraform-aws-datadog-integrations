module "service" {
  source       = "../../modules/pagerduty"
  service_key  = "1234567890"
  service_name = "testing_tf"
  s3_bucket    = "wiser-one-ci"
}
