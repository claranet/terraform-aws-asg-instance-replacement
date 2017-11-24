import boto3
import collections
import elb


autoscaling = boto3.client('autoscaling')


class lazyproperty(object):

    def __init__(self, function):
        self._function = function

    def __get__(self, obj, _=None):
        if obj is None:
            return self
        value = self._function(obj)
        setattr(obj, self._function.__name__, value)
        return value


class AutoScalingGroup(dict):

    # If the ASG has an InstanceReplacement tag with any of the following
    # values then it will not be managed by this module. If the value is
    # blank or any other value, it will be managed. If there is no tag,
    # it will not be managed.
    DISABLED_TAGS = set((
        '0',
        'disabled',
        'false',
        'no',
        'off',
    ))

    # These Auto Scaling processes will be disabled while this module
    # is managing and replacing instances.
    SCALING_PROCESSES = (
        'AlarmNotification',
        'AZRebalance',
        'Launch',
        'ScheduledActions',
    )

    # Instance status values used to determine various important states.
    READY_STATUS = 'All:Ready'
    LAUNCHING_STATUSES = set((
        'LifecycleState:Pending',
        'LifecycleState:PendingWait',
    ))
    TERMINATING_STATUSES = set((
        'HealthStatus:Unhealthy',
        'LifecycleState:Terminating',
    ))

    @lazyproperty
    def instance_health(self):
        """
        Returns a dictionary of { InstanceId: [ InstanceState ] } using data
        from any attached load balancers.

        """

        result = collections.defaultdict(list)

        for load_balancer_name in self['LoadBalancerNames']:
            instance_states = elb.describe_instance_health(
                LoadBalancerName=load_balancer_name,
            )
            for instance_state in instance_states:
                instance_id = instance_state['InstanceId']
                result[instance_id].append(instance_state)

        return result

    @lazyproperty
    def instances(self):
        """
        Returns a list of instances in this ASG. The list has helper
        properties for filtering on various details of the instances.

        """

        return InstanceList(
            instances=self['Instances'],
            asg=self,
        )

    @lazyproperty
    def is_managed(self):
        """
        Returns a boolean indicating whether the ASG has instance replacement
        management enabled via tags.

        """

        for tag in self['Tags']:
            if tag['Key'] == 'InstanceReplacement':
                if tag['Value'].lower() in self.DISABLED_TAGS:
                    return False
                return True
        return False

    @lazyproperty
    def is_suspend_processes_required(self):
        """
        Returns a boolean indicating whether scaling processes need
        to be suspended so that instances can be replaced safely.

        """

        if self.instances.old:
            suspended_processes = set()
            for process in self['SuspendedProcesses']:
                suspended_processes.add(process['ProcessName'])
            for process in self.SCALING_PROCESSES:
                if process not in suspended_processes:
                    return True
        return False

    @lazyproperty
    def target_health(self):
        """
        Returns a dictionary of { InstanceId: [ TargetHealthDescription ] }
        using data from any attached target groups.

        """

        result = collections.defaultdict(list)

        targets = []
        for instance in self['Instances']:
            targets.append({
                'Id': instance['InstanceId'],
            })

        for target_group_arn in self['TargetGroupARNs']:
            target_health_descriptions = elb.describe_target_health(
                TargetGroupArn=target_group_arn,
                Targets=targets,
            )
            for target_health_description in target_health_descriptions:
                instance_id = target_health_description['Target']['Id']
                result[instance_id].append(target_health_description)

        return result

    def get_instance_status(self, instance):
        """
        Returns a string indicating the overall instance status. This is in
        the form of "Field:Value" and can come from data in the ASG or related
        Target Groups. If the instance is healthy and in service then the
        READY_STATUS constant value is returned.

        """

        lifecycle_state = instance.get('LifecycleState')
        if lifecycle_state != 'InService':
            return 'LifecycleState:{}'.format(lifecycle_state)

        health_status = instance.get('HealthStatus')
        if health_status != 'Healthy':
            return 'HealthStatus:{}'.format(health_status)

        instance_id = instance['InstanceId']

        for desc in self.target_health[instance_id]:
            state = desc['TargetHealth']['State']
            if state != 'healthy':
                reason = desc['TargetHealth']['Reason']
                return 'TargetHealth:{}'.format(reason)

        for state in self.instance_health[instance_id]:
            if state['State'] != 'InService':
                return 'InstanceHealth:{}'.format(state['ReasonCode'])

        return self.READY_STATUS

    def increase_desired_capacity(self):
        """
        Increases the desired capacity by 1.

        """

        response = autoscaling.update_auto_scaling_group(
            AutoScalingGroupName=self['AutoScalingGroupName'],
            DesiredCapacity=self['DesiredCapacity'] + 1,
        )
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception('ERROR: {}'.format(response))

    def log(self, message, *args):
        """
        Prints a message with the ASG name prefixed.

        """

        prefix = '[{}] '.format(self['AutoScalingGroupName'])
        print(prefix + message.format(*args))

    def resume_processes(self, scaling_processes=None):
        """
        Resumes the specified suspended Auto Scaling processes,
        or all suspended processes if none were specified.

        """

        kwargs = {
            'AutoScalingGroupName': self['AutoScalingGroupName'],
        }
        if scaling_processes:
            kwargs['ScalingProcesses'] = scaling_processes

        response = autoscaling.resume_processes(**kwargs)
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception('ERROR: {}'.format(response))

    def set_instance_unhealthy(self, instance):
        """
        Sets the instance health to unhealthy so the ASG will terminate it.

        """

        response = autoscaling.set_instance_health(
            InstanceId=instance['InstanceId'],
            HealthStatus='Unhealthy',
            ShouldRespectGracePeriod=False,
        )
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception('ERROR: {}'.format(response))

    def suspend_processes(self):
        """
        Suspends the scaling processes that interfere with the instance
        replacement process.

        """

        response = autoscaling.suspend_processes(
            AutoScalingGroupName=self['AutoScalingGroupName'],
            ScalingProcesses=self.SCALING_PROCESSES,
        )
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception('ERROR: {}'.format(response))


class InstanceList(collections.UserList):
    """
    A list of instances with helper properties for filtering.

    """

    def __init__(self, instances, asg):
        self.data = instances
        self.asg = asg

    @lazyproperty
    def launching(self):
        instances = []
        for instance in self:
            status = self.asg.get_instance_status(instance)
            if status in self.asg.LAUNCHING_STATUSES:
                instances.append(instance)
        return self.__class__(instances, self.asg)

    @lazyproperty
    def new(self):
        instances = []
        asg_lc = self.asg['LaunchConfigurationName']
        for instance in self:
            instance_lc = instance.get('LaunchConfigurationName')
            if instance_lc == asg_lc:
                instances.append(instance)
        return self.__class__(instances, self.asg)

    @lazyproperty
    def old(self):
        instances = []
        asg_lc = self.asg['LaunchConfigurationName']
        for instance in self:
            instance_lc = instance.get('LaunchConfigurationName')
            if instance_lc != asg_lc:
                instances.append(instance)
        return self.__class__(instances, self.asg)

    @lazyproperty
    def terminating(self):
        instances = []
        for instance in self:
            status = self.asg.get_instance_status(instance)
            if status in self.asg.TERMINATING_STATUSES:
                instances.append(instance)
        return self.__class__(instances, self.asg)

    @lazyproperty
    def unready(self):
        instances = []
        for instance in self:
            status = self.asg.get_instance_status(instance)
            if status != self.asg.READY_STATUS:
                instances.append(instance)
        return self.__class__(instances, self.asg)


def describe_auto_scaling_groups(**kwargs):
    """
    Describes one or more Auto Scaling groups.

    """

    paginator = autoscaling.get_paginator('describe_auto_scaling_groups')
    pages = paginator.paginate(**kwargs)
    for page in pages:
        if page['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception('ERROR: {}'.format(page))
        for group in page['AutoScalingGroups']:
            yield group


def describe_auto_scaling_instances(**kwargs):
    """
    Describes one or more Auto Scaling instances.

    """

    paginator = autoscaling.get_paginator('describe_auto_scaling_instances')
    pages = paginator.paginate(**kwargs)
    for page in pages:
        if page['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception('ERROR: {}'.format(page))
        for instance in page['AutoScalingInstances']:
            yield instance
