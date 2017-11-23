import boto3

elbv2 = boto3.client('elbv2')


def describe_target_health(**kwargs):
    """
    Describes the health of the specified targers or all of your targets.

    """

    response = elbv2.describe_target_health(**kwargs)
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception('ERROR: {}'.format(response))

    return response['TargetHealthDescriptions']
