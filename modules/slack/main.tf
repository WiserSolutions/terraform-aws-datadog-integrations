data "template_file" "slack_channel" {
  template = "${file("${path.module}/templates/slack.json")}"

  vars {
    channel_name = "#${var.channel_name}"
  }
}

resource "aws_s3_bucket_object" "object" {
  bucket = "${var.s3_bucket}"

  #key    = "datadog/integration type/service"
  key     = "${var.s3_base}/channel-${var.channel_name}.json"
  content = "${data.template_file.slack_channel.rendered}"

  # Should be encrypted
  server_side_encryption = "aws:kms"
  tags                   = "${var.tags}"
}
