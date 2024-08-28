provider "aws" {
  region = "us-east-1"
  profile = "default"
}

locals {
  subnet_1 = "subnet-06e72e051f2b1d0fb"
  subnet_2 = "subnet-0033c9900b2306718"
}

data "aws_subnet" "subnet-1" {
  id = local.subnet_1
}

data "aws_subnet" "subnet-2" {
  id = local.subnet_2
}

resource "aws_efs_file_system" "filesystem-1" {
  creation_token = "filesystem-1"
  encrypted = false
  tags = {
    Name = "filesystem-1"
  }
}

resource "aws_efs_mount_target" "filesystem-1-target" {
  file_system_id = aws_efs_file_system.filesystem-1.id
  subnet_id      = data.aws_subnet.subnet-1.id
}


resource "aws_efs_mount_target" "filesystem-2-target" {
  file_system_id = aws_efs_file_system.filesystem-1.id
  subnet_id      = data.aws_subnet.subnet-2.id
}