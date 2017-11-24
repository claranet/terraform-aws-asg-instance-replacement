import boto3


elb = boto3.client('elb')
elbv2 = boto3.client('elbv2')


def describe_instance_health(**kwargs):
    """
    Describes the state of instances with respect to the
    specified load balancer.

    """

    response = elb.describe_instance_health(**kwargs)
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception('ERROR: {}'.format(response))

    return response['InstanceStates']


def describe_target_health(**kwargs):
    """
    Describes the health of the specified targers or all of your targets.

    """

    response = elbv2.describe_target_health(**kwargs)
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception('ERROR: {}'.format(response))

    return response['TargetHealthDescriptions']
