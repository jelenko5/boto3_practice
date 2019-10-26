import boto3
from datetime import datetime
import dateutil.tz


SKIP_ENVS = ['production']
RUNNING_CODE = 16
STOPPED_CODE = 80
serbian_tz = dateutil.tz.gettz('Europe/Belgrade')

NOW = datetime.utcnow()
NOW_SERBIA = NOW.astimezone(serbian_tz)

print("NOW_UTC: " + datetime.strftime(NOW, "%d-%m-%YT%H:%M:%S"))
print("NOW_SERBIA: " + datetime.strftime(NOW_SERBIA, "%d-%m-%YT%H:%M:%S"))


def extract_tags(tags_list):
    tags = dict()
    for tag in tags_list:
        tags[tag['Key']] = tag['Value']
    return tags


def check_ec2_instance(instance):
    tags = extract_tags(instance.tags)

    if not tags or 'env' not in tags.keys() or 'time' not in tags.keys():
        print("Checked instance: {}. Invalid tags. Skipping.".format(instance.id))
        return
    if tags['env'] in SKIP_ENVS:
        print("Checked instance: {}. env={}. Skipping.".format(instance.id, tags['env']))
        return

    opening_hour = int(tags['time'][0:2])
    closing_hour = int(tags['time'][3:])
    opening_time = datetime(NOW_SERBIA.year, NOW_SERBIA.month, NOW_SERBIA.day, hour=opening_hour, tzinfo=serbian_tz)
    closing_time = datetime(NOW_SERBIA.year, NOW_SERBIA.month, NOW_SERBIA.day, hour=closing_hour, tzinfo=serbian_tz)

    print('Checking instance {}, with state "{}"; at: {}'.format(instance.id,
                                                                 instance.state['Name'],
                                                                 datetime.strftime(NOW_SERBIA, "%d-%m-%YT%H:%M:%S")))
    print('Instance opening time: {}; closing time: {}'.format(datetime.strftime(opening_time, "%d-%m-%YT%H:%M:%S"),
                                                               datetime.strftime(closing_time, "%d-%m-%YT%H:%M:%S")))

    if opening_time < NOW_SERBIA < closing_time:
        if instance.state['Code'] != RUNNING_CODE:
            print('Starting instance {}'.format(instance.id))
            response = instance.start()
            response_code = response['ResponseMetadata']['HTTPStatusCode']
            if response_code != 200:
                print('Something went wrong! Response code: {}. Please check!'.format(response_code))
            else:
                print('Instance started successfully!')
        else:
            print('Working during working hours! Nothing to do here.')
    else:
        if instance.state['Code'] == RUNNING_CODE:
            print('Stopping instance {}'.format(instance.id))
            response = instance.stop()
            response_code = response['ResponseMetadata']['HTTPStatusCode']
            if response_code != 200:
                print('Something went wrong! Response code: {}. Please check!'.format(response_code))
            else:
                print('Instance stopped successfully!')
        else:
            print('Not working during non-working hours! Nothing to do here.')


def check_rds_instance(rds, instance):
    instance_arn = instance['DBInstanceArn']
    instance_id = instance['DBInstanceIdentifier']
    tags_list = rds.list_tags_for_resource(ResourceName=instance_arn)['TagList']
    tags = extract_tags(tags_list)

    if not tags or 'env' not in tags.keys() or 'time' not in tags.keys():
        print("Checked instance: {}. Invalid tags. Skipping.".format(instance_id))
        return
    if tags['env'] in SKIP_ENVS:
        print("Checked instance: {}. env={}. Skipping.".format(instance_id, tags['env']))
        return

    opening_hour = int(tags['time'][0:2])
    closing_hour = int(tags['time'][3:])
    opening_time = datetime(NOW_SERBIA.year, NOW_SERBIA.month, NOW_SERBIA.day, hour=opening_hour, tzinfo=serbian_tz)
    closing_time = datetime(NOW_SERBIA.year, NOW_SERBIA.month, NOW_SERBIA.day, hour=closing_hour, tzinfo=serbian_tz)

    print('Checking instance {}, with state "{}"; at: {}'.format(instance_id,
                                                                 instance['DBInstanceStatus'],
                                                                 datetime.strftime(NOW_SERBIA, "%d-%m-%YT%H:%M:%S")))
    print('Instance opening time: {}; closing time: {}'.format(datetime.strftime(opening_time, "%d-%m-%YT%H:%M:%S"),
                                                               datetime.strftime(closing_time, "%d-%m-%YT%H:%M:%S")))

    if opening_time < NOW_SERBIA < closing_time:
        if instance['DBInstanceStatus'].lower() == 'stopped':
            print('Starting instance {}'.format(instance_id))
            try:
                response = rds.start_db_instance(DBInstanceIdentifier=instance_id)
                response_code = response['ResponseMetadata']['HTTPStatusCode']
                if response_code != 200:
                    print('Something went wrong! Response code: {}. Please check!'.format(response_code))
                else:
                    print('Instance started successfully!')
            except Exception as e:
                print(e)
                return
        else:
            print('Available during working hours! Nothing to do here.')
    else:
        if instance['DBInstanceStatus'].lower() == 'available':
            print('Stopping instance {}'.format(instance_id))
            try:
                response = rds.stop_db_instance(DBInstanceIdentifier=instance_id)
                response_code = response['ResponseMetadata']['HTTPStatusCode']
                if response_code != 200:
                    print('Something went wrong! Response code: {}. Please check!'.format(response_code))
                else:
                    print('Instance stopped successfully!')
            except Exception as e:
                print(e)
                return
        else:
            print('Not available during non-working hours! Nothing to do here.')


# if __name__ == '__main__':
def lambda_handler(event, context):
    """ Lambda function which is supposed to turn on EC2 and RDS instances during working hours and stop them during
    non-working hours. 
    Requirements:
    - `env` tag on instances. Only instances with `env != "production"` tag will be affected
    - `time` tag on instances. Defines opening and closing hours in format HH-HH
    - cron job scheduler that triggers lambda function
    - aws cli for local usage (configured with `~/.aws/credentials` and `~/.aws/config` files)
    """

    ec2 = boto3.resource('ec2')
    filters = [
        {
            'Name': 'tag:time',
            'Values': ['*']
        }
    ]

    print('**************** CHECKING EC2 INSTANCES ****************')
    for instance in ec2.instances.filter(Filters=filters):
        print('================================================================')
        check_ec2_instance(instance)
        print('================================================================')

    rds = boto3.client('rds')

    print('**************** CHECKING RDS INSTANCES ****************')
    for instance in rds.describe_db_instances()['DBInstances']:
        print('================================================================')
        check_rds_instance(rds, instance)
        print('================================================================')

    print('\n Done!')
