variable "name" {
  description = "Name to use for resources"
  default     = "tf-aws-asg-instance-replacement"
}

variable "schedule" {
  description = "Schedule for running the Lambda function"
  default     = "rate(1 minute)"
}

variable "timeout" {
  description = "Lambda function timeout"
  default     = "60"
}

variable "lambda_layers" {
  description = "List of Lambda Layer Version ARNs to attach to the Lambda Function"
  default     = []
}

variable "python_version" {
  type        = string
  description = "Specify the Python version to be used"
  default     = "python3.9"
}
