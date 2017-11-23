import boto3

ec2 = boto3.client('ec2')


def terminate_instance(instance):
    """
    Terminates an EC2 instance.

    """

    instance_id = instance['InstanceId']

    response = ec2.terminate_instances(
        InstanceIds=[instance_id]
    )
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception('ERROR: {}'.format(response))

    return response['TerminatingInstances']
