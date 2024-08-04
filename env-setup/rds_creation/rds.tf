provider "aws" {
  region = "us-east-1"
}
resource "aws_db_instance" "database-1" {
  identifier        = "database-1"
  allocated_storage = 20
  db_subnet_group_name = "project-public"
  engine              = "mysql"
  engine_version      = "8.0"
  instance_class      = "db.t3.micro"
  password            = "mysqlpassword"
  skip_final_snapshot = true
  storage_encrypted   = false
  username            = "sqlsqlsql"
  apply_immediately   = true
  publicly_accessible = true

  provisioner "local-exec" {
    command = "python rds_insert.py mysql+pymysql://sqlsqlsql:mysqlpassword@${aws_db_instance.database-1.endpoint}"
    when = create
  }
}


output "rds_endpoint" {
  value = aws_db_instance.database-1.endpoint
}