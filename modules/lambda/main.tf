//
// Lambda module
//
# TODO: Add full tag support

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.lambda_name}"
  retention_in_days = 14

  tags {
    "Description" = "${var.lambda_name} lambda logs"
    "Environment" = "${var.environment}"
    "terraform"   = "true"
  }
}

# IAM give lambda access to read ec2, r
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type = "Service"

      identifiers = [
        "lambda.amazonaws.com",
      ]
    }

    effect = "Allow"
  }
}

data "aws_iam_policy_document" "lambda_perms" {
  statement {
    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DeleteNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "kms:Decrypt",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "s3:GetObject",
      "s3:ListBucket",
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue",
      "secretsmanager:ListSecrets",
    ]

    effect    = "Allow"
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "LambdaPerms" {
  name   = "LambdaSeviceMonitorPermissions"
  role   = "${aws_iam_role.iam_for_lambda.id}"
  policy = "${data.aws_iam_policy_document.lambda_perms.json}"
}

resource "aws_iam_role" "iam_for_lambda" {
  name               = "${var.lambda_name}"
  path               = "/lambda/"
  assume_role_policy = "${data.aws_iam_policy_document.lambda_assume_role.json}"
}

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${var.source_dir}"
  output_path = "${var.lambda_name}.zip"
}

resource "aws_lambda_function" "this" {
  depends_on = [
    "aws_cloudwatch_log_group.lambda",
  ]

  description      = "${var.lambda_desc}"
  filename         = "${data.archive_file.lambda.output_path}"
  function_name    = "${var.lambda_name}"
  role             = "${aws_iam_role.iam_for_lambda.arn}"
  handler          = "${var.lambda_handler}"
  source_code_hash = "${base64sha256(file("${data.archive_file.lambda.output_path}"))}"
  runtime          = "python2.7"
  publish          = true
  timeout          = 20

  environment {
    variables = "${var.lambda_env_vars}"
  }

  tags {
    "Description" = "${var.lambda_desc}"

    #"Stack" =
    "Terraform" = "true"
  }
}

//
// Trigger on S3 change
//
# https://www.terraform.io/docs/providers/aws/r/s3_bucket_notification.html

data "aws_s3_bucket" "parts" {
  bucket = "${var.s3_bucket}"
}

resource "aws_lambda_permission" "allow_s3_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.this.function_name}"
  principal     = "s3.amazonaws.com"
  source_arn    = "${data.aws_s3_bucket.parts.arn}"
}
