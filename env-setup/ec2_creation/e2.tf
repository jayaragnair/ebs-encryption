provider "aws" {
  region = "us-east-1"
  profile = "default"
}


resource "aws_instance" "al2023" {
  count = 2
  ami = "ami-06b21ccaeff8cd686"
  instance_type = "t2.micro"
  tags = {
    Name = "test-encryption-${count.index}"
  }
  root_block_device {
    encrypted = false
    }
}