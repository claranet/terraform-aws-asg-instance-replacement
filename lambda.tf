module "lambda" {
  source = "github.com/claranet/terraform-aws-lambda?ref=v1.1.0"

  function_name = var.name
  description   = "Manages ASG instance replacement"
  handler       = "main.lambda_handler"
  runtime       = var.python_version
  layers        = var.lambda_layers
  timeout       = var.timeout

  source_path = "${path.module}/lambda"

  policy = {
    json = data.aws_iam_policy_document.lambda.json
  }
}

data "aws_iam_policy_document" "lambda" {
  statement {
    effect = "Allow"

    actions = [
      "autoscaling:DescribeAutoScalingGroups",
      "autoscaling:DescribeAutoScalingInstances",
      "autoscaling:ResumeProcesses",
      "autoscaling:SetInstanceHealth",
      "autoscaling:SuspendProcesses",
      "autoscaling:UpdateAutoScalingGroup",
      "ec2:TerminateInstances",
      "elasticloadbalancing:DescribeInstanceHealth",
      "elasticloadbalancing:DescribeTargetHealth",
    ]

    resources = [
      "*",
    ]
  }
}
