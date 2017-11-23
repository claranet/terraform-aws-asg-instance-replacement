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
