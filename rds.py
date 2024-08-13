import boto3
from botocore.exceptions import ClientError
from botocore.waiter import WaiterModel, create_waiter_with_client
from datetime import datetime
import time


class RDSStoppedWaiter:
    waiter_name = "RDSStopped"
    waiter_config = {
        "version": 2,
        "waiters": {
            "RDSStopped": {
                "delay": 30,
                "operation": "DescribeDBInstances",
                "maxAttempts": 123,
                "acceptors": [{
                    "expected": "stopped",
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

    def __init__(self, rds_identifier: str, region: str = 'us-east-1', profile: str = 'default', key: str = 'alias/aws/rds'):
        session = boto3.session.Session(profile_name=profile, region_name=region)

        self.rds_identifier = rds_identifier
        self.key = key
        self._rds_client = session.client('rds')
        self._rds_details = self._rds_client.describe_db_instances(DBInstanceIdentifier=rds_identifier)['DBInstances'][0]
        self._rds_stop_waiter = RDSStoppedWaiter.get_waiter(self._rds_client)
        self._rds_available_waiter = self._rds_client.get_waiter('db_instance_available')
        self._snapshot_created_waiter = self._rds_client.get_waiter('db_snapshot_available')

        self._delay = 30
        self._max_attempts = 100

        if self.pre_checks():
            pass
        else:
            # Exits the whole execution if pre-checks fails
            exit()
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
                print("-- Pre checks passed")
                return True

        except ClientError as err:
            if err.response['Error']['Code'] == 'DBInstanceNotFoundFault':
                raise Exception("RDS not found")

    def stop_rds(self):
        print(f"-- Stopping RDS: {self.rds_identifier}--unencrypted")
        self._rds_client.stop_db_instance(
            DBInstanceIdentifier=f"{self.rds_identifier}--unencrypted"
        )
        self._rds_stop_waiter.wait(
            DBInstanceIdentifier=f"{self.rds_identifier}--unencrypted",
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

    def copy_snapshot(self):
        snapshot = self._rds_client.copy_db_snapshot(
            SourceDBSnapshotIdentifier=self.rds_identifier,
            TargetDBSnapshotIdentifier=f"{self.rds_identifier}-encrypted",
            KmsKeyId=self.key,
            CopyTags=True
        )

        self._snapshot_created_waiter.wait(
            DBSnapshotIdentifier=f"{self.rds_identifier}-encrypted",
            WaiterConfig={
                'Delay': self._delay,
                'MaxAttempts': self._max_attempts
            }
        )

        print(f"-- Snapshot: {snapshot['DBSnapshot']['DBSnapshotIdentifier']} has been created")
        return snapshot['DBSnapshot']['DBSnapshotIdentifier']

    def create_encrypted_db(self):
        # kwargs = dict(CustomIamInstanceProfile=self._rds_details['CustomIamInstanceProfile'])
        # self._rds_client.restore_db_instance_from_db_snapshot(a=b for a, b in kwargs if b is not None)
        self._rds_client.restore_db_instance_from_db_snapshot(
            DBInstanceIdentifier=f"{self.rds_identifier}-encrypted",
            DBSnapshotIdentifier=f"{self.rds_identifier}-encrypted",
            DBSubnetGroupName=self._rds_details['DBSubnetGroup']['DBSubnetGroupName'],
            MultiAZ=self._rds_details['MultiAZ'],
            PubliclyAccessible=self._rds_details['PubliclyAccessible'],
            AutoMinorVersionUpgrade=self._rds_details['AutoMinorVersionUpgrade'],
            OptionGroupName=self._rds_details['OptionGroupMemberships'][0]['OptionGroupName'],
            Tags=self._rds_details['TagList'],
            StorageType=self._rds_details['StorageType'],
            VpcSecurityGroupIds=[sg['VpcSecurityGroupId'] for sg in self._rds_details['VpcSecurityGroups']],
            CopyTagsToSnapshot=True,
            DBParameterGroupName=self._rds_details['DBParameterGroups'][0]['DBParameterGroupName'],
            DeletionProtection=False,
        )

        self._rds_available_waiter.wait(
            DBInstanceIdentifier=f"{self.rds_identifier}-encrypted",
            WaiterConfig={
                'Delay': self._delay,
                'MaxAttempts': self._max_attempts
            }
        )

        print(f"-- RDS : {self.rds_identifier}-encrypted has been created")

    def swap_db_name(self):
        self._rds_client.modify_db_instance(
            DBInstanceIdentifier=self.rds_identifier,
            NewDBInstanceIdentifier=f"{self.rds_identifier}-unencrypted",
            ApplyImmediately=True
        )

        # Time to change to renaming
        time.sleep(30)

        self._rds_available_waiter.wait(
            DBInstanceIdentifier=self.rds_identifier,
            WaiterConfig={
                'Delay': self._delay,
                'MaxAttempts': self._max_attempts
            }
        )

        self._rds_client.modify_db_instance(
            DBInstanceIdentifier=f"{self.rds_identifier}-encrypted",
            NewDBInstanceIdentifier=self.rds_identifier,
            ApplyImmediately=True
        )

        # Time to change to renaming
        time.sleep(30)

        self._rds_available_waiter.wait(
            DBInstanceIdentifier=f"{self.rds_identifier}-encrypted",
            WaiterConfig={
                'Delay': self._delay,
                'MaxAttempts': self._max_attempts
            }
        )

        print("-- DB Names swapped")

    def start_encryption(self):
        self.create_snapshot()
        self.copy_snapshot()
        self.create_encrypted_db()
        self.swap_db_name()
        # self.stop_rds()


if __name__ == "__main__":
    print(datetime.now())
    EncryptRDS(rds_identifier='database-1').start_encryption()
    print(datetime.now())

