module "channel" {
  source       = "../../modules/slack"
  channel_name = "test-srv-1a"
  s3_bucket    = "wiser-infra-automation"
}
