variable "channel_name" {
  description = "Slack channel name"
  default     = ""
}

variable "s3_base" {
  description = "Base path in S3 bucket for Slack configuration pieces"
  default     = "datadog/integration/slack"
}

variable "s3_bucket" {
  description = "AWS S3 bucket for storing Slack configuration pieces"
}

variable "tags" {
  description = "Tags to apply to object"
  type        = "map"
  default     = {}
}
