module "channel" {
  source       = "../../modules/slack"
  channel_name = ""
  s3_bucket    = "wiser-infra-automation"
}
