variable "environment" {
  description = "Deploy environment"
  default     = ""
}
variable "lambda_desc" {
  description = "Description of lambda"
}
variable "lambda_env_vars" {
  description = "Environment variable to provide to lambda"
  type        = "map"
  default     = {}
}
variable "lambda_handler" {
  description = "Lambda handler"
}

variable "lambda_name" {
  description = "Name of lambda"
}

variable "s3_bucket" {
  description = "S3 Bucket to provide rights to access"
}

variable "source_dir" {
  description = "Directory that contains lambda source"
}

#variable "trigger_s3_prefix" {}
#variable "trigger_s3_suffix" {}
/*
  environment {
    variables = {
      ENVIRONMENT = "${var.environment}"
      #LAMBDA_CONFIG = "s3://${aws_s3_bucket.monitoring.id}/service-monitor/config.json"
      LAMBDA_CONFIG = "${var.lambda_config}"
      LOG_LEVEL     = "${var.log_level}"
    }
  }
/**/
