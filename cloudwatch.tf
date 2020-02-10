# Trigger the Lambda function with these ASG and EC2 events.

resource "aws_cloudwatch_event_rule" "events" {
  name = "${var.name}-events"

  event_pattern = <<PATTERN
{
  "source": [
    "aws.autoscaling",
    "aws.ec2"
  ],
  "detail-type": [
    "EC2 Instance Launch Successful",
    "EC2 Instance State-change Notification",
    "EC2 Instance Terminate Successful"
  ]
}
PATTERN

}

resource "aws_cloudwatch_event_target" "events" {
  target_id = "${var.name}-events"
  rule      = aws_cloudwatch_event_rule.events.name
  arn       = module.lambda.function_arn
}

resource "aws_lambda_permission" "events" {
  statement_id  = "${var.name}-events"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.events.arn
}

# Also trigger it with a schedule.

resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${var.name}-schedule"
  schedule_expression = var.schedule
}

resource "aws_cloudwatch_event_target" "schedule" {
  target_id = "${var.name}-schedule"
  rule      = aws_cloudwatch_event_rule.schedule.name
  arn       = module.lambda.function_arn
}

resource "aws_lambda_permission" "schedule" {
  statement_id  = "${var.name}-schedule"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}
