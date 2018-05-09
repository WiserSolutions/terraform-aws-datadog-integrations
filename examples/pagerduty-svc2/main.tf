module "service" {
  source       = "../../modules/pagerduty"
  service_key  = "123456789012"
  service_name = "test-srv-2"
  s3_bucket    = "wiser-one-ci"
}
