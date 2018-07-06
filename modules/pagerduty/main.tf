data "template_file" "pagerduty_service" {
  template = "${file("${path.module}/templates/pagerduty.json")}"

  vars {
    default      = "${var.datadog_default}"
    service_key  = "${var.service_key}"
    service_name = "${var.service_name}"
  }
}

resource "aws_s3_bucket_object" "object" {
  bucket = "${var.s3_bucket}"
  acl    = "bucket-owner-full-control"

  #key    = "datadog/integration type/service"
  key     = "${var.s3_base}/service-${var.service_name}.json"
  content = "${data.template_file.pagerduty_service.rendered}"

  # Should be encrypted
  server_side_encryption = "AES256"
  tags                   = "${var.tags}"
}
