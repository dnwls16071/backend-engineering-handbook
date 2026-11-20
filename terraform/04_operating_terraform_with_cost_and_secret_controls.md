# Operating Terraform with Cost and Secret Controls

팀에서 Terraform을 운영할 때는 변경이 재현되는지, 누가 적용하는지, 비용과 비밀이 어디에 남는지를 함께 다룬다. 리소스 생성 계획을 보는 것과 실제 운영 조건을 검토하는 일에는 서로 다른 확인 항목이 있다.

## 1. AWS 비용과 변경 관리

| 검토 지점 | 확인할 내용 |
| --- | --- |
| 적용 전 | 계정·리전, VPC 피어링과 Endpoint의 경로, NAT Gateway·로드 밸런서·공인 IPv4처럼 사용 기간이나 처리량에 따라 과금되는 리소스 |
| 적용 후 | 실제 생성된 리소스와 소유 태그, 비용 추세, 로그와 객체 버전의 보존 기간 |
| 환경 정리 | 대상 상태의 삭제 계획, Terraform 밖에서 생성된 리소스, 남아 있는 S3 객체 버전·스냅샷 |

계획은 어떤 인프라를 바꿀지 보여 준다. 비용은 예상 사용량·리전에 따라 별도로 추정하고 AWS Budgets 등에서 실제 추세를 확인한다. 팀 작업에서는 PR에 변경 목적, 적용 환경, 관측 포인트와 되돌리는 조건을 남긴다. [AWS Pricing Calculator](https://calculator.aws/) · [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html) · [Amazon VPC Pricing](https://aws.amazon.com/vpc/pricing/)

## 2. Terraform과 OpenTofu의 사용 조건

HashiCorp Terraform 1.6.0 이상 소스에 적용되는 BSL은 사용 방식에 대한 조건을 둔다. OpenTofu는 MPL 2.0 라이선스 기반으로 배포되는 별도 프로젝트다. 제품에 내장하거나 외부에 호스팅하는 방식, 사내 표준, 사용할 버전을 실제 라이선스 본문과 맞춰 검토한다.

도구를 바꿀 때는 HCL 파싱뿐 아니라 공급자·모듈 버전, 백엔드 설정과 상태 읽기, CI에서 실행하는 명령까지 확인한다. 동일한 상태에 여러 엔진을 번갈아 적용하기 전에 테스트 환경의 백업과 계획으로 검증한다. [Terraform 라이선스](https://github.com/hashicorp/terraform/blob/main/LICENSE) · [HashiCorp Licensing FAQ](https://www.hashicorp.com/en/license-faq) · [OpenTofu 라이선스](https://github.com/opentofu/opentofu/blob/main/LICENSE)

## 3. SOPS로 암호화된 구성 관리

SOPS는 YAML·JSON 등 구성의 값을 암호화한다. 파일 경로에 따라 사용할 age 수신자나 AWS KMS 키를 `.sops.yaml`의 `creation_rules`로 정할 수 있다. 개인 실습은 age 공개키를 선택할 수 있고, 팀은 AWS KMS 권한과 연결할 수 있다. Git에 암호화된 파일을 올리고, 복호화에 필요한 개인 키나 KMS 권한은 별도 경로에서 관리한다. [SOPS Reference](https://getsops.io/docs/reference/)

| 위치 | 보호할 대상 |
| --- | --- |
| Git | 암호화된 설정, 파일별 키 선택 규칙 |
| 로컬·CI 실행 환경 | 복호화 권한, 평문 파일·로그·출력 |
| Terraform 상태·저장된 계획 | 공급자로 전달한 비밀 값이 결과 파일에 남는지와 접근 권한 |

`sensitive`는 Terraform 출력에서 값을 가리는 데 쓰인다. 그 값을 일반 리소스에 넘기면 상태나 저장된 계획에 남을 수 있다. 상태에 보관할 필요가 없는 값은 런타임의 비밀 참조로 다루거나, 해당 Terraform·공급자 기능이 지원하는 ephemeral 값과 write-only 인수를 검토한다. [Terraform · Manage Sensitive Data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data)
