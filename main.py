import argparse
import openpyxl
import os
from ec2 import EncryptEC2
from rds import EncryptRDS
from efs import EncryptEFS


def parse_arguments():
    parser = argparse.ArgumentParser(description='Encrypt AWS Resources')
    resource_parser = parser.add_subparsers(dest='resource_parser')

    ec2 = resource_parser.add_parser('ec2', help="For encrypting EC2 instances with EBS volumes")
    ebs = resource_parser.add_parser('ebs', help="For encrypting unattached EBS volumes")
    rds = resource_parser.add_parser('rds', help="For encrypting RDS databases")
    efs = resource_parser.add_parser('efs', help="For encrypting EFS filesystems")

    ec2_parser = ec2.add_subparsers(dest='type_parser')
    ec2_bulk = ec2_parser.add_parser('bulk', help="For bulk execution Excel file path with instance details")
    ec2_single = ec2_parser.add_parser('single', help="For single instance ")
    ec2_bulk.add_argument('-f', '--file', metavar='input-file.xlsx', nargs='?', required=True)
    ec2_single.add_argument('-i', '--instance', help="Single instance id", required=True)
    ec2_single.add_argument('-r', '--region', help="AWS region", required=True)
    ec2_single.add_argument('-p', '--profile', help="AWS profile", default='default')
    ec2_single.add_argument('-k', '--key', help="KMS key id [optional]. If not provided, AWS managed key will be used")

    ebs_parser = ebs.add_subparsers(dest='type_parser')
    ebs_bulk = ebs_parser.add_parser('bulk', help="For bulk execution Excel file path with EBS details")
    ebs_single = ebs_parser.add_parser('single', help="For single EBS volume ")
    ebs_bulk.add_argument('-f', '--file', metavar='input-file.xlsx', nargs='?', required=True)
    ebs_single.add_argument('-v', '--volume', help="Single EBS volume id", required=True)
    ebs_single.add_argument('-r', '--region', help="AWS region", required=True)
    ebs_single.add_argument('-p', '--profile', help="AWS profile", default='default')
    ebs_single.add_argument('-k', '--key', help="KMS key id [optional]. If not provided, AWS managed key will be used")

    rds_parser = rds.add_subparsers(dest='type_parser')
    rds_bulk = rds_parser.add_parser('bulk', help="For bulk execution Excel file path with rds details")
    rds_single = rds_parser.add_parser('single', help="For single rds instance ")
    rds_bulk.add_argument('-f', '--file', metavar='input-file.xlsx', nargs='?', required=True)
    rds_single.add_argument('-v', '--volume', help="Single rds  ARN", required=True)
    rds_single.add_argument('-r', '--region', help="AWS region", required=True)
    rds_single.add_argument('-p', '--profile', help="AWS profile", default='default')
    rds_single.add_argument('-k', '--key', help="KMS key id [optional]. If not provided, AWS managed key will be used")

    efs_parser = efs.add_subparsers(dest='type_parser')
    efs_bulk = efs_parser.add_parser('bulk', help="For bulk execution Excel file path with EFS details")
    efs_single = efs_parser.add_parser('single', help="For single EFS filesystem ")
    efs_bulk.add_argument('-f', '--file', metavar='input-file.xlsx', nargs='?', required=True)
    efs_single.add_argument('-v', '--volume', help="Single EFS ARN", required=True)
    efs_single.add_argument('-r', '--region', help="AWS region", required=True)
    efs_single.add_argument('-p', '--profile', help="AWS profile", default='default')
    efs_single.add_argument('-k', '--key', help="KMS key id [optional]. If not provided, AWS managed key will be used")

    # return parser.parse_args(['ec2', '-h'])
    return parser.parse_args()

def file_exists(file):
    if os.path.exists(file):
        return True
    else:
        raise Exception("Oops, that path doesn't exist")


def bulk_execution(args):
    wb = openpyxl.load_workbook(args.file)
    ws = wb.active
    heading = []
    first_row = ws.iter_rows(max_row=1, values_only=True)
    for i in first_row:
        heading.extend(list(i))
    resource_row = heading.index('resourceid')
    region_row = heading.index('region')
    profile_row = heading.index('profile')
    try:
        key_row = heading.index('Key')
    except ValueError:
        key_row = None
    data = ws.iter_rows(min_row=2, values_only=True)
    for row in data:
        resource_id = row[resource_row]
        region = row[region_row]
        profile = row[profile_row]
        print(resource_id, region, profile)

        if args.resource_parser == 'ec2':
            if key_row:
                key = row[key_row]
                EncryptEC2(instance_id=resource_id, region=region, profile=profile, key=key).start_encryption()
            else:
                print("Proceeding without custom key, AWS managed key will be used for encryption")
                EncryptEC2(instance_id=resource_id, region=region, profile=profile).start_encryption()

        elif args.resource_parser == 'ebs':
            if key_row:
                key = row[key_row]
                EncryptEC2(instance_id=resource_id, region=region, profile=profile, key=key).start_encryption()
            else:
                print("Proceeding without custom key, AWS managed key will be used for encryption")
                EncryptEC2(instance_id=resource_id, region=region, profile=profile).start_encryption()

        elif args.resource_parser == 'rds':
            if key_row:
                key = row[key_row]
                EncryptRDS(rds_identifier=resource_id, region=region, profile=profile, key=key).start_encryption()
            else:
                print("Proceeding without custom key, AWS managed key will be used for encryption")
                EncryptRDS(rds_identifier=resource_id, region=region, profile=profile).start_encryption()

        elif args.resource_parser == 'efs':
            if key_row:
                key = row[key_row]
                EncryptEFS(efs_id=resource_id, region=region, profile=profile, key=key).start_encryption()
            else:
                print("Proceeding without custom key, AWS managed key will be used for encryption")
                EncryptEFS(efs_id=resource_id, region=region, profile=profile).start_encryption()

        else:
            pass


def single_execution(args):
    resource_id = args.instance
    region = args.region
    profile = args.profile
    try:
        key = args.key
    except ValueError:
        key = None

    if args.resource_parser == 'ec2':
        if key:
            EncryptEC2(instance_id=resource_id, region=region, profile=profile, key=key).start_encryption()
        else:
            print("Proceeding without custom key, AWS managed key will be used for encryption")
            EncryptEC2(instance_id=resource_id, region=region, profile=profile).start_encryption()

    elif args.resource_parser == 'ebs':
        if key:
            EncryptEC2(instance_id=resource_id, region=region, profile=profile, key=key).start_encryption()
        else:
            print("Proceeding without custom key, AWS managed key will be used for encryption")
            EncryptEC2(instance_id=resource_id, region=region, profile=profile).start_encryption()

    elif args.resource_parser == 'rds':
        if key:
            EncryptRDS(rds_identifier=resource_id, region=region, profile=profile, key=key).start_encryption()
        else:
            print("Proceeding without custom key, AWS managed key will be used for encryption")
            EncryptRDS(rds_identifier=resource_id, region=region, profile=profile).start_encryption()

    elif args.resource_parser == 'efs':
        if key:
            EncryptEFS(efs_id=resource_id, region=region, profile=profile, key=key).start_encryption()
        else:
            print("Proceeding without custom key, AWS managed key will be used for encryption")
            EncryptEFS(efs_id=resource_id, region=region, profile=profile).start_encryption()
    else:
        pass
    # if key:
    #     EncryptEC2(instance_id=instance_id, region=region, profile=profile, key=key).start_encryption()
    # else:
    #     EncryptEC2(instance_id=instance_id, region=region, profile=profile).start_encryption()


if __name__ == "__main__":
    arguments = parse_arguments()

    if arguments.type_parser == 'bulk':
        if file_exists(arguments.file):
            bulk_execution(arguments)
        else:

            raise Exception("Oops, that path doesn't exist")
    if arguments.type_parser == 'single':
        single_execution(arguments)
