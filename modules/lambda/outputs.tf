

output "lambda_arn" {
  description = ""
  value       = "${aws_lambda_function.this.arn}"
}
output "s3_bucket_id" {
  description = ""
  value       = "${data.aws_s3_bucket.parts.id}"
}
