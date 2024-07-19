import argparse
import openpyxl
import os
from ec2 import EncryptEC2


def parse_arguments():
    parser = argparse.ArgumentParser(description='Encrypt EC2 instance')
    sub_parser = parser.add_subparsers(dest='sub_command')

    bulk = sub_parser.add_parser('bulk', help="For bulk execution Excel file path with instance details")
    single = sub_parser.add_parser('single', help="For single instance ")

    bulk.add_argument('-f', '--file', metavar='input-file.xlsx', nargs='?', required=True)
    single.add_argument('-i', '--instance', help="Single instance id", required=True)
    single.add_argument('-r', '--region', help="AWS region", required=True)
    single.add_argument('-p', '--profile', help="AWS profile", default='default')
    single.add_argument('-k', '--key', help="KMS key id [optional]. If not provided, AWS managed key will be used")
    return parser.parse_args()


def file_exists(file):
    if os.path.exists(file):
        return True
    else:
        raise Exception("Oops, that path doesn't exist")


def bulk_execution(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    heading = []
    first_row = ws.iter_rows(max_row=1, values_only=True)
    for i in first_row:
        heading.extend(list(i))
    instance_row = heading.index('InstanceID')
    region_row = heading.index('Region')
    account_row = heading.index('Account')
    try:
        key_row = heading.index('Key')
    except ValueError:
        key_row = None
    data = ws.iter_rows(min_row=2, values_only=True)
    for row in data:
        instance_id = row[instance_row]
        region = row[region_row]
        account = row[account_row]
        print(instance_id, region, account)
        if key_row:
            key = row[key_row]
            EncryptEC2(instance_id=instance_id, region=region, profile=account, key=key).start_encryption()
        else:
            print("Proceeding without custom key, AWS managed key will be used for encryption")
            EncryptEC2(instance_id=instance_id, region=region, profile=account).start_encryption()


def single_execution(args):
    instance_id = args.instance
    region = args.region
    account = args.profile
    try:
        key = args.key
    except ValueError:
        key = None
    if key:
        EncryptEC2(instance_id=instance_id, region=region, profile=account, key=key).start_encryption()
    else:
        EncryptEC2(instance_id=instance_id, region=region, profile=account).start_encryption()


if __name__ == "__main__":
    arguments = parse_arguments()
    if arguments.sub_command == 'bulk':
        if file_exists(arguments.file):
            bulk_execution(arguments.file)
        else:
            raise Exception("Oops, that path doesn't exist")
    if arguments.sub_command == 'single':
        single_execution(arguments)

