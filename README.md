# tf-aws-asg-instance-replacement

This module automatically replaces old instances when an Auto Scaling Group's Launch Configuration changes. In other words: rolling AMI updates and instance type changes.

It tries to increase an ASG's desired capacity to launch new instances, but will never increase the maximum size, so it should be safe to use on just about any ASG.

It sets old instances as unhealthy one at a time to gradually replace them with new instances.

It waits for new instances to be completely healthy, ready and in service before proceeding to replace more instances. It will wait for ASG lifecycle hooks and Target Group health checks if they are being used.

## Caution

__Use this module with caution; it terminates healthy instances.__

Care must be taken when using this module with certain types of instances, such as RabbitMQ and Elasticsearch cluster nodes. If these instances are using only ephemeral or in-memory storage, then terminating them too quickly could result in data loss.

In this situation, use Auto Scaling Lifecycle Hooks on the instances to wait until everything is truly healthy (e.g. cluster status green) before putting the instance in service.

## Components

### Lambda function

Use this module once per AWS account to create the Lambda function and associated resources required to perform instance replacement.

The Lambda function runs on a schedule to ensure that all enabled ASGs within the AWS account are replacing instances if the launch configuration has changed. For example, if an ASG is changed to use a different AMI, the scheduled function will detect this and start replacing old instances.

The Lambda function is also triggered whenever an instance is launched or terminated. This makes the process event-driven where possible.

### ASG tags

Add an `InstanceReplacement` tag to an ASG to enable instance replacement. If the value is one of `0, disabled, false, no, off` then it will be disabled. Any other value, including a blank string, will enable instance replacement for that ASG.

## Example

```js

// Create the Lambda function and associated resources once per AWS account.

module "asg_instance_replacement" {
  source = "tf-aws-asg-instance-replacement"
}

// Enable this module for an ASG by adding the InstanceReplacement tag.

resource "aws_autoscaling_group" "asg" {
  ...

  tag {
    key                 = "InstanceReplacement"
    value               = ""
    propagate_at_launch = false
  }

  ...
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|:----:|:-----:|:-----:|
| name | Name to use for resources | string | `tf-aws-asg-instance-replacement` | no |
| schedule | Schedule for running the Lambda function | string | `rate(1 minute)` | no |
| timeout | Lambda function timeout | string | `60` | no |
