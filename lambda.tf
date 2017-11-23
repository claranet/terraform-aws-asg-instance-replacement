module "lambda" {
  source = "../tf-aws-lambda"

  function_name = "${var.name}"
  description   = "Manages ASG instance replacement"
  handler       = "main.lambda_handler"
  runtime       = "python3.6"
  timeout       = "${var.timeout}"

  source_path = "${path.module}/lambda"

  attach_policy = true
  policy        = "${data.aws_iam_policy_document.lambda.json}"
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
      "elasticloadbalancing:DescribeTargetHealth",
    ]

    resources = [
      "*",
    ]
  }
}
