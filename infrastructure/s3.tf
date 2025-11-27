# S3 bucket for Velero backups
resource "aws_s3_bucket" "velero_backup" {
  bucket = "velero-backup-${random_id.bucket_suffix.hex}"
  
  tags = {
    Name        = "velero-backup-bucket"
    Environment = "dev"
    Terraform   = "true"
    Purpose     = "velero-backups"
  }
}

# Random suffix to ensure bucket name uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Block public access to the bucket
resource "aws_s3_bucket_public_access_block" "velero_backup" {
  bucket = aws_s3_bucket.velero_backup.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for backup data protection
resource "aws_s3_bucket_versioning" "velero_backup" {
  bucket = aws_s3_bucket.velero_backup.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle rule to manage old versions and reduce costs
resource "aws_s3_bucket_lifecycle_configuration" "velero_backup" {
  bucket = aws_s3_bucket.velero_backup.id

  rule {
    id     = "velero_backup_lifecycle"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "velero_backup" {
  bucket = aws_s3_bucket.velero_backup.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}