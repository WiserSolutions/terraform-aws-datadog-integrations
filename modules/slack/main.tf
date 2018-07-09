# Expect Slack channel name to be of format: mon-<env>-<service short name>
# Auto disable if:
#   Channel name is empty
#   Channel name has format mon-<env>-<service short name> but nothing after second -

locals {
  enabled = "${length(replace(var.channel_name, "/(mon-\\w+-)(.*)$/", "$2")) > 0 ? 1 : 0}"
}

data "template_file" "slack_channel" {
  count    = "${local.enabled}"
  template = "${file("${path.module}/templates/slack.json")}"

  vars {
    channel_name = "#${var.channel_name}"
  }
}

resource "aws_s3_bucket_object" "object" {
  count  = "${local.enabled}"
  bucket = "${var.s3_bucket}"
  acl    = "bucket-owner-full-control"

  #key    = "datadog/integration type/service"
  key     = "${var.s3_base}/channel-${var.channel_name}.json"
  content = "${data.template_file.slack_channel.rendered}"

  # Should be encrypted
  server_side_encryption = "AES256"
  tags                   = "${var.tags}"
}
