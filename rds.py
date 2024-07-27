import boto3
from botocore.exceptions import ClientError
from botocore.waiter import WaiterModel, create_waiter_with_client


class RDSStoppedWaiter:
    waiter_name = "RDSStopped"
    waiter_config = {
        "version": 2,
        "waiters": {
            "RDSStopped": {
                "delay": 15,
                "operation": "DescribeDBInstances",
                "maxAttempts": 30,
                "acceptors": [{
                    "expected": "available",
                    "matcher": "pathAny",
                    "state": "success",
                    "argument": "DBInstances[].DBInstanceStatus"
                }]
            }
        }
    }

    @staticmethod
    def get_waiter(client: boto3.client):
        waiter_model = WaiterModel(RDSStoppedWaiter.waiter_config)
        rds_stopped_waiter = create_waiter_with_client(RDSStoppedWaiter.waiter_name, waiter_model, client)
        return rds_stopped_waiter


class EncryptRDS:

    def __init__(self, rds_identifier: str, region: str = 'us-east-1', profile: str = 'default', key: str = 'alias/aws/ebs'):
        session = boto3.session.Session(profile_name=profile, region_name=region)

        self.rds_identifier = rds_identifier
        self.key = key
        self._rds_client = session.client('rds')
        self._rds_details = self._rds_client.describe_db_instances(DBInstanceIdentifier=rds_identifier)['DBInstances'][0]
        self._rds_stop_waiter = RDSStoppedWaiter.get_waiter(self._rds_client)
        self._rds_available_waiter = self._rds_client.get_waiter('db_instance_available')
        self._snapshot_created_waiter = self._rds_client.get_waiter('db_snapshot_available')

        self._delay = 5
        self._max_attempts = 100

        if self.pre_checks():
            pass
        else:
            # Exits the whole execution if pre-checks fails
            # exit()
            pass

    def pre_checks(self) -> bool:
        """ Checks if the rds is already encrypted or supports encrypted volumes."""
        print("-- Performing pre checks")
        try:
            # Checks if RDS is encrypted already.
            if self._rds_details['StorageEncrypted']:
                print("All volumes are already encrypted")
                return False
            else:
                pass

            # Checks if the RDS type supports encryption
            rds_type = self._rds_details['DBInstanceClass']
            if rds_type.startswith(('m1', 'm2', 't2')):
                print(f"RDS type {rds_type} is not supported for encryption")
                return False
            else:
                print("Pre checks passed")
                return True

        except ClientError as err:
            if err.response['Error']['Code'] == 'DBInstanceNotFoundFault':
                raise Exception("RDS not found")

    def stop_rds(self):
        print(f"-- Stopping RDS: {self.rds_identifier}")
        self._rds_client.stop_db_instance(
            DBInstanceIdentifier=self.rds_identifier
        )
        self._rds_stop_waiter.wait(
            DBInstanceIdentifier=self.rds_identifier,
            WaiterConfig={
                'Delay': self._delay,
                'MaxAttempts': self._max_attempts
            }
        )
        print(f"-- RDS : {self.rds_identifier} stopped")

    def create_snapshot(self):
        print(f"-- Creating snapshots")
        snapshot = self._rds_client.create_db_snapshot(
            DBSnapshotIdentifier=self.rds_identifier,
            DBInstanceIdentifier=self.rds_identifier,
            Tags=self._rds_details['TagList']
        )
        self._snapshot_created_waiter.wait(
            DBSnapshotIdentifier=self.rds_identifier,
            WaiterConfig={
                'Delay': self._delay,
                'MaxAttempts': self._max_attempts
            }
        )

        print(f"-- Snapshot: {snapshot['DBSnapshot']['DBSnapshotIdentifier']} created")
        return snapshot['DBSnapshot']['DBSnapshotIdentifier']

    def copy_snapshot(self, snapshot_id):
        snapshot = self._rds_client.copy_db_snapshot(
            SourceDBSnapshotIdentifier=self.rds_identifier,
            TargetDBSnapshotIdentifier=f"{self.rds_identifier}-encrypted",
            KmsKeyId=self.key,
            CopyTags=True
        )

        self._snapshot_created_waiter.wait(
            DBSnapshotIdentifier=f"{self.rds_identifier}--encrypted",
            WaiterConfig={
                'Delay': self._delay,
                'MaxAttempts': self._max_attempts
            }
        )

        print(f"-- Snapshot: {snapshot['DBSnapshot']['DBSnapshotIdentifier']} encrypted")
        return snapshot['DBSnapshot']['DBSnapshotIdentifier']

    def create_encrypted_db(self, snapshot):
        self._rds_client.restore_db_instance_from_db_snapshot(
            DBInstanceIdentifier=f"{self.rds_identifier}--encrypted",
            DBSnapshotIdentifier=f"{self.rds_identifier}--encrypted",
            DBSubnetGroupName=self._rds_details['DBSubnetGroup']['DBSubnetGroupName'],
            MultiAZ=self._rds_details['MultiAZ'],
            PubliclyAccessible=self._rds_details['PubliclyAccessible'],
            AutoMinorVersionUpgrade=True|False,
            LicenseModel='string',
            DBName='string',
            Engine='string',
            Iops=123,
            OptionGroupName='string',
            Tags=[
                {
                    'Key': 'string',
                    'Value': 'string'
                },
            ],
            StorageType='string',
            TdeCredentialArn='string',
            TdeCredentialPassword='string',
            VpcSecurityGroupIds=[
                'string',
            ],
            Domain='string',
            DomainFqdn='string',
            DomainOu='string',
            DomainAuthSecretArn='string',
            DomainDnsIps=[
                'string',
            ],
            CopyTagsToSnapshot=True|False,
            DomainIAMRoleName='string',
            EnableIAMDatabaseAuthentication=True|False,
            EnableCloudwatchLogsExports=[
                'string',
            ],
            ProcessorFeatures=[
                {
                    'Name': 'string',
                    'Value': 'string'
                },
            ],
            UseDefaultProcessorFeatures=True|False,
            DBParameterGroupName='string',
            DeletionProtection=True|False,
            EnableCustomerOwnedIp=True|False,
            CustomIamInstanceProfile='string',
            BackupTarget='string',
            NetworkType='string',
            StorageThroughput=123,
            DBClusterSnapshotIdentifier='string',
            AllocatedStorage=123,
            DedicatedLogVolume=True|False,
            CACertificateIdentifier='string',
            EngineLifecycleSupport='string'
        )


if __name__ == "__main__":
    EncryptRDS(rds_identifier='database-1').stop_rds()

