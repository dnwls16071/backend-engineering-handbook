# Advanced VPC Connectivity with Terraform

VPC 연결 방식은 두 네트워크 간 경로가 필요한지, 특정 서비스에 사설로 접근해야 하는지에 따라 정한다. [02번 VPC 구성](02_provisioning_aws_network_storage_and_iam.md)에 이어 두 번째 VPC와 사설 연결을 검토한다.

## 1. 멀티 VPC 주소와 라우팅

`10.20.0.0/16`과 `10.30.0.0/16`처럼 네트워크가 겹치지 않도록 주소를 잡는다. 라우팅 테이블은 각 서브넷의 목적지별 다음 경로를 정한다. 연결을 설치한 뒤에도 반대 방향 경로, DNS, 보안 그룹과 네트워크 ACL을 확인해야 한다. 상태 저장 방식의 보안 그룹은 허용한 연결의 응답을 추적하고, 네트워크 ACL은 요청과 응답 방향을 각각 평가한다. [AWS VPC 라우팅](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html) · [VPC 네트워크 ACL](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)

## 2. 연결 방식 고르기

| 방식 | 필요한 연결 | 검토 항목 |
| --- | --- | --- |
| VPC Peering | 두 VPC 사이의 사설 IP 라우팅 | CIDR 비중첩, 양쪽 라우팅, 수락 절차. 세 번째 VPC에 대한 전이 라우팅은 제공하지 않는다. |
| Gateway Endpoint | VPC에서 지원되는 S3·DynamoDB 서비스로 사설 접근 | 대상 라우팅 테이블과 Endpoint 정책, IAM·버킷 정책 |
| Interface Endpoint | AWS 서비스나 PrivateLink Endpoint Service로 접속 | 소비자 VPC의 ENI, 보안 그룹, DNS, 지원 가용 영역 |

자체 서비스를 노출하는 PrivateLink 예에서는 제공자 VPC의 NLB를 Endpoint Service에 연결하고, 소비자 VPC에서 Interface Endpoint를 만든다. 서비스 제공 권한과 연결 수락 여부, 소비자 Endpoint의 보안 그룹, DNS 이름을 확인한다. 소비자는 지정한 서비스 엔드포인트로 접근한다. [VPC Peering](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html) · [Gateway Endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html) · [PrivateLink Endpoint Service](https://docs.aws.amazon.com/vpc/latest/privatelink/create-endpoint-service.html)

## 3. 같은 계정·리전의 실습 확장

다음 블록은 02번 구성의 `aws_vpc.lab`과 `aws_route_table.private`를 참조한다. 기존 VPC와 두 번째 VPC의 프라이빗 라우팅 테이블에 왕복 경로를 추가한다. `auto_accept`는 이 예제처럼 같은 계정·리전인 경우에 사용한다. 다른 소유자나 리전에서는 상대 측 수락과 공급자 구성을 별도로 설계한다.

```hcl
resource "aws_vpc" "second" {
  cidr_block           = "10.30.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
}

resource "aws_subnet" "second_private" {
  vpc_id            = aws_vpc.second.id
  availability_zone = var.availability_zone
  cidr_block        = "10.30.11.0/24"
}

resource "aws_route_table" "second_private" {
  vpc_id = aws_vpc.second.id
}

resource "aws_route_table_association" "second_private" {
  subnet_id      = aws_subnet.second_private.id
  route_table_id = aws_route_table.second_private.id
}

resource "aws_vpc_peering_connection" "lab_second" {
  vpc_id      = aws_vpc.lab.id
  peer_vpc_id = aws_vpc.second.id
  auto_accept = true
}

resource "aws_route" "lab_to_second" {
  route_table_id            = aws_route_table.private.id
  destination_cidr_block    = aws_vpc.second.cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.lab_second.id
}

resource "aws_route" "second_to_lab" {
  route_table_id            = aws_route_table.second_private.id
  destination_cidr_block    = aws_vpc.lab.cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.lab_second.id
}

resource "aws_vpc_endpoint" "lab_s3" {
  vpc_id            = aws_vpc.lab.id
  service_name      = "com.amazonaws.ap-northeast-2.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
}
```

S3 Gateway Endpoint는 이 예제에서 첫 VPC의 지정 라우팅 테이블에만 연결한다. 두 번째 VPC에서 피어링을 통해 첫 VPC의 Gateway Endpoint를 공유하는 구성으로 해석하지 않는다. 실제 통신을 확인할 때는 두 VPC에서 각각 출발해 경로, 정책, DNS 결과를 대조한다. [S3 Gateway Endpoint 고려사항](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html) · [Interface Endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html)
