# Provisioning AWS Networking, Storage, and IAM

VPC는 주소와 라우팅의 경계다. 서브넷과 라우팅 테이블이 통신 경로를 정하고, 보안 그룹과 IAM은 각각 네트워크 접근과 API 권한을 제어한다. 이 예제는 한 가용 영역에서 기본 리소스의 연결을 보여 준다. [AWS VPC](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html) · [VPC 라우팅 예제](https://docs.aws.amazon.com/vpc/latest/userguide/route-table-options.html)

## 1. VPC, 서브넷, IGW, NAT Gateway

퍼블릭 서브넷에는 인터넷 게이트웨이(IGW)로 향하는 경로를 둔다. 인스턴스가 인터넷과 직접 통신하려면 IPv4의 경우 퍼블릭 IPv4 주소 등도 필요하다. 프라이빗 서브넷의 기본 경로를 퍼블릭 NAT Gateway에 연결하면 외부로 나가는 IPv4 연결을 만들 수 있다. NAT Gateway가 있는 퍼블릭 서브넷에는 IGW 경로가 있어야 한다. 아래 예제에서는 비용이 발생하는 NAT 생성을 입력값으로 선택한다. [AWS NAT Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)

```hcl
terraform {
  required_version = ">= 1.10.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "availability_zone" {
  type        = string
  description = "AWS 리전에 속한 가용 영역 이름"
}

variable "enable_nat" {
  type    = bool
  default = false
}

provider "aws" {
  region = "ap-northeast-2"
}

resource "aws_vpc" "lab" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.lab.id
  availability_zone = var.availability_zone
  cidr_block        = "10.20.1.0/24"
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.lab.id
  availability_zone = var.availability_zone
  cidr_block        = "10.20.11.0/24"
}

resource "aws_internet_gateway" "lab" {
  vpc_id = aws_vpc.lab.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.lab.id
}

resource "aws_route" "public_default" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.lab.id
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  count  = var.enable_nat ? 1 : 0
  domain = "vpc"
}

resource "aws_nat_gateway" "lab" {
  count         = var.enable_nat ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public.id

  depends_on = [aws_internet_gateway.lab]
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.lab.id
}

resource "aws_route" "private_default" {
  count                  = var.enable_nat ? 1 : 0
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.lab[0].id
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}
```

## 2. S3와 애플리케이션의 IAM 역할

아래 블록을 같은 구성에 더한다. 버킷 이름은 AWS 파티션 내에서 고유한 값을 선택한다. 예제는 퍼블릭 액세스 차단과 버전 관리를 지정한다. EC2 역할의 신뢰 정책은 누가 역할을 맡을 수 있는지, 권한 정책은 맡은 뒤 어떤 작업을 할 수 있는지 정한다. 이 예제에서는 `assets/` 아래 객체 읽기만 허용한다. 목록 조회가 요구된다면 버킷 ARN에 대한 `s3:ListBucket`과 필요한 접두어 조건을 별도로 검토한다. [S3 Block Public Access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html) · [IAM Roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)

```hcl
variable "bucket_name" {
  type        = string
  description = "AWS 파티션에서 고유한 S3 버킷 이름"
}

resource "aws_s3_bucket" "assets" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket                  = aws_s3_bucket.assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_iam_role" "application" {
  name_prefix = "tf-lab-app-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "read_assets" {
  name = "read-assets"
  role = aws_iam_role.application.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:GetObject"
      Resource = "${aws_s3_bucket.assets.arn}/assets/*"
    }]
  })
}

resource "aws_iam_instance_profile" "application" {
  name_prefix = "tf-lab-app-"
  role        = aws_iam_role.application.name
}
```

EC2에 이 역할을 연결하려면 인스턴스 또는 시작 템플릿에 인스턴스 프로파일을 지정한다. 실제 계획에서는 생성할 NAT·EIP, 선택한 리전과 가용 영역, IAM 권한 범위를 확인한다. 실습 상태와 팀 협업은 [03번](03_terraform_state_variables_and_team_workflows.md), 여러 가용 영역과 애플리케이션 계층 배치는 [06번](06_three_tier_aws_infrastructure_and_terraform_import.md)에서 다룬다. [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
