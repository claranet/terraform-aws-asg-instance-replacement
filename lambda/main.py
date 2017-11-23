import autoscaling
import ec2
import itertools


def lambda_handler(event, context):

    print('event: {}'.format(event))

    # If this is an ASG event then it will have an ASG name.
    detail = event['detail']
    asg_name = detail.get('AutoScalingGroupName')

    # If this is an EC2 event then it will have an instance id.
    # If the instance is part of an ASG then get its name.
    if not asg_name:
        instance_id = detail.get('instance-id')
        if instance_id:
            instances = autoscaling.describe_auto_scaling_instances(
                InstanceIds=[instance_id]
            )
            for instance in instances:
                asg_name = instance['AutoScalingGroupName']
                break

    # If this is an ASG or EC2 event then manage just the one ASG.
    # If this is a scheduled event then manage all ASGs.
    if asg_name:
        asgs = autoscaling.describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name],
        )
    else:
        asgs = autoscaling.describe_auto_scaling_groups()

    # Replace any old instances in any of the ASGs.
    for asg in asgs:
        asg = autoscaling.AutoScalingGroup(asg)
        if asg.is_managed:
            replace_old_instances(asg)


def replace_old_instances(asg):
    """
    Replaces old instances in an ASG. This function is called repeatedly,
    triggered by various events and schedules. Each time it looks at the
    current state of the ASG to determine and perform the next action
    required to replace all old instances. When all instances in the ASG
    have the ASG's current Launch Configuration, then it is done.

    """

    if asg.is_suspend_processes_required:
        asg.log('suspending processes')
        asg.suspend_processes()

    if len(asg.instances) > asg['MaxSize']:

        # Bad State: the number of instance exceeds the ASG max size

        # ASGs can launch new instances while old instances are still
        # draining connections, leading to more instances than the max
        # size. This can be bad for certain ASGs where the max size should
        # never be exceeded.

        # To avoid this happening, the Launch process is suspended during
        # updates. If for some reason an instance still happens to launch
        # and exceed the max size, like if Terraform undid the Launch
        # suspension, then terminate instances here.

        terminations_required = len(asg.instances) - asg['MaxSize']

        instances_in_termination_order = itertools.chain(
            asg.instances.terminating,
            asg.instances.launching,
            asg.instances.unready,
            asg.instances.new,
            asg.instances,
        )

        terminating_instance_ids = set()

        for instance in instances_in_termination_order:

            instance_id = instance['InstanceId']

            if instance_id in terminating_instance_ids:
                continue

            status = asg.get_instance_status(instance)

            if status == 'LifecycleState:Terminating':
                asg.log(
                    'max size exceeded, waiting for instance {} to terminate',
                    instance_id,
                )
            else:
                asg.log(
                    'max size exceeded, terminating instance {} {}',
                    instance_id,
                    status,
                )
                ec2.terminate_instance(instance)

            terminating_instance_ids.add(instance_id)

            if len(terminating_instance_ids) == terminations_required:
                break

        # Next: State C

    elif asg['DesiredCapacity'] < asg['MaxSize'] and not asg.instances.new:

        # State A: desired capacity should be increased

        # When starting the replacement process (asg.instances.new is empty),
        # and the desired capacity can be increased without exceeding the max
        # size, increase it to make the ASG launch new instances.

        # This could potentially trigger multiple times, launching more
        # than 1 new instance at once, but it won't exceed the max size,
        # and the other steps won't terminate more than 1 instance at once.

        asg.log('increasing desired capacity to add new instance')
        asg.increase_desired_capacity()

        # Next: State B

    elif len(asg.instances) < asg['DesiredCapacity']:

        # State B: waiting for ASG to launch new instances

        # When there aren't as many instances as desired, resume the
        # launch process and wait for the ASG to launch more instances.

        asg.log('resuming launch scaling process')
        asg.resume_processes(['Launch'])

        # Next: State C

    elif asg.instances.new.unready or asg.instances.old.terminating:

        # State C: waiting for instances

        # If new instances have launched but they're not ready yet,
        # wait for them to become ready.

        # Manual intervention may be required when stuck at this step, and the
        # new instance isn't becoming ready by itself. If the AMI is broken,
        # perhaps release a new one. If a manual fix is required on the new
        # instance, consider doing that. If the new instance relies on other
        # instances to be updated, consider manually terminating the old
        # instances in the ASG so it launches more new instances.

        for instance in asg.instances.new.unready:
            asg.log(
                'waiting for new instance {} {}',
                instance['InstanceId'],
                asg.get_instance_status(instance),
            )

        # If old instances are terminating, wait for them to finish.

        for instance in asg.instances.old.terminating:
            asg.log(
                'waiting for old instance {} to terminate, {}',
                instance['InstanceId'],
                asg.get_instance_status(instance),
            )

        # Next: State D or E

    elif asg.instances.old:

        # State D: teminate one old instance

        if asg.instances.old.unready:
            instance = asg.instances.old.unready[0]
        else:
            instance = asg.instances.old
        asg.log(
            'setting old instance {} {} to unhealthy',
            instance['InstanceId'],
            asg.get_instance_status(instance),
        )
        asg.set_instance_unhealthy(instance)

        # Next: State C

    elif asg['SuspendedProcesses']:

        # State E: resume processes and it's done

        asg.log('resuming all processes')
        asg.resume_processes()
        asg.log('complete')
