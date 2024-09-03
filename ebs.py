import boto3
from botocore.exceptions import ClientError


class EncryptEBS:
    def __int__(self, volume_id: str, region: str = 'us-east-1', profile: str = 'default', key: str = 'alias/aws/ebs'):
        session = boto3.session.Session(profile_name=profile, region_name=region)
        self.volume_id = volume_id
        self.key = key
        self._ebs_client = session.client('ec2')  # Boto3 EC2 client provides necessary actions for EBS
        self._ebs_resource = session.resource('ec2')
        self._ebs_available_waiter = self._ebs_client.get_waiter('volume_available')
        self._snapshot_created_waiter = self._ebs_client.get_waiter('snapshot_completed')

        self._delay = 5
        self._max_attempts = 60


    def get_az(self) -> str:
        pass

    def create_snapshots(self, volume_ids: list) -> list:
        created_snapshots = []
        for volume in volume_ids:
            volume_resource = self._ebs_resource.Volume(volume)

            # Pulling tags and excluding the ones that starts with keyword "aws" as aws blocks creating these manually
            final_tags = []
            for tag in volume_resource.tags:
                if tag['Key'].startswith('aws'):
                    pass
                else:
                    final_tags.append(tag)
            response = self._ebs_client.create_snapshot(
                VolumeId=volume,
                TagSpecifications=[
                    {
                        'ResourceType': 'snapshot',
                        'Tags': final_tags
                    }
                ]
            )
            self._snapshot_created_waiter.wait(
                SnapshotIds=[
                    response['SnapshotId'],
                ],
                WaiterConfig={
                    'Delay': self._delay,
                    'MaxAttempts': self._max_attempts
                }
            )
            created_snapshots.append(response['SnapshotId'])
            print(f"-- {response['SnapshotId']} created")
        return created_snapshots

    def create_volume(self, snapshot_ids: list, availability_zone: str) -> list:
        created_volumes = []
        for snapshot in snapshot_ids:
            snapshot_resource = self._ebs_resource.Snapshot(snapshot)
            volume_type = ''
            for tag in snapshot_resource.tags:
                if tag['Key'] == 'volume-type':
                    volume_type = tag['Value']

            # If there is a requirement to convert all volumes to latest gp3 version
            # if volume_type == 'gp2' or volume_type == 'io1' or volume_type == 'standard':
            #     volume_type = 'gp3'

            response = self._ebs_client.create_volume(
                AvailabilityZone=availability_zone,
                Encrypted=True,
                KmsKeyId=self.key,
                SnapshotId=snapshot,
                VolumeType=volume_type,
                TagSpecifications=[
                    {
                        'ResourceType': 'volume',
                        'Tags': snapshot_resource.tags
                    }
                ]
            )
            self._ebs_available_waiter.wait(
                VolumeIds=[
                    response['VolumeId'],
                ],
                WaiterConfig={
                    'Delay': self._delay,
                    'MaxAttempts': self._max_attempts
                }
            )
            created_volumes.append(response['VolumeId'])
        print(f"-- Volumes: {created_volumes} created")
        return created_volumes

    def start_encryption(self):
        snapshots = self.create_snapshots([self.volume_id])
        self.create_volume(snapshots, )
