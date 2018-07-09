variable "datadog_default" {
  description = "Default Pagerduty service for Datadog (@pagerduty)"
  default     = ""
}

variable "service_key" {
  description = "PagerDuty service integration key"
  default     = ""
}

variable "service_name" {
  description = "PagerDuty service name as used in Datadog"
}

variable "s3_base" {
  description = "Base path in S3 bucket for PagerDuty configuration pieces"
  default     = "datadog/integration/pagerduty"
}

variable "s3_bucket" {
  description = "AWS S3 bucket for storing PagerDuty configuration pieces"
}

variable "tags" {
  description = "Tags to apply to object"
  type        = "map"
  default     = {}
}
