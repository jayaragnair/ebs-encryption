import boto3
from botocore.exceptions import ClientError
import time
# from sys import exit


class EncryptEFS:

    def __init__(self, efs_id: str, region: str = 'us-east-1', profile: str = 'default', key: str = 'alias/aws/elasticfilesystem'):
        session = boto3.session.Session(profile_name=profile, region_name=region)
        self.region = region
        self.efs_identifier = efs_id
        self.key = key
        self._efs_client = session.client('efs')
        # self._efs_available_waiter = self._efs_client.get_waiter('db_instance_available')
        # self._snapshot_created_waiter = self._efs_client.get_waiter('db_snapshot_available')

        self._delay = 30
        self._max_attempts = 100

        if self.pre_checks():
            self._pre_checks_passed = True
            self._efs_details = self._efs_client.describe_file_systems(FileSystemId=self.efs_identifier)['FileSystems'][0]
        else:
            # Exits the whole execution if pre-checks fails
            self._pre_checks_passed = False

    def pre_checks(self) -> bool:
        """ Checks if the efs is already encrypted"""
        print("-- Performing pre checks")
        try:
            # Checks if efs is encrypted already.
            if self._efs_client.describe_file_systems(FileSystemId=self.efs_identifier)['FileSystems'][0]['Encrypted']:
                print("EFS is already encrypted")
                return False
            else:
                print("-- Pre checks passed")
                return True

        except ClientError as err:
            if err.response['Error']['Code'] == 'FileSystemNotFound':
                raise Exception(f"EFS {self.efs_identifier} not found")

    def replicate_efs(self):
        print("-- Creating replication configuration")
        response = self._efs_client.create_replication_configuration(
            SourceFileSystemId=self.efs_identifier,
            Destinations=[
                {
                    'Region': self.region,
                    'KmsKeyId': self.key
                },
            ]
        )

        fs_id = response['Destinations'][0]['FileSystemId']

        print("-- Waiting for replication to complete")
        replicated = False
        while not replicated:
            try:
                replication_details = self._efs_client.describe_replication_configurations(FileSystemId=fs_id)
                last_replicated = replication_details['Replications'][0]['Destinations'][0]['LastReplicatedTimestamp']
                replicated = True
            except KeyError:
                time.sleep(15)

        print(f"-- Replication completed to destination efs : {fs_id}")
        return fs_id

    def failover_to_replica(self):
        self._efs_client.delete_replication_configuration(
            SourceFileSystemId=self.efs_identifier
        )
        print("-- Creating standalone encrypted efs from replica")

        #     Wait for the fail-over to complete by describing the replication status
        replication_completed = False
        while not replication_completed:
            try:
                self.describe_replica(self.efs_identifier)
                time.sleep(30)
            except ClientError as err:
                if err.response['Error']['Code'] == 'ReplicationNotFound':
                    replication_completed = True

    def describe_replica(self, fs_id: str):
        self._efs_client.describe_replication_configurations(
            FileSystemId=fs_id
        )

    def copy_tags_if_exists(self, fs_id: str):
        self._efs_client.create_tags(
            FileSystemId=fs_id,
            Tags=self._efs_details['Tags']
        )

    def start_encryption(self):
        if self._pre_checks_passed:
            created_replica = self.replicate_efs()
            self.failover_to_replica()
            self.copy_tags_if_exists(created_replica)
            print(f"-- Encryption completed. Mount the new encrypted efs : {created_replica}")


if __name__ == "__main__":
    EncryptEFS(efs_id="fs-07008af7021d6d28c").start_encryption()
