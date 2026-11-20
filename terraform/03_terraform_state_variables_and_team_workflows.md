# Terraform State, Variables, and Team Workflows

Backend는 상태를 어디에 보관할지 정하고, 입력 변수와 함수는 같은 구성에서 환경별 차이를 표현한다. 팀에서는 검토한 변경만 공유 상태에 적용하는 작업 흐름도 함께 마련한다.

## 1. S3 원격 상태와 잠금

버킷은 별도 부트스트랩 구성이나 관리 절차로 준비한다. 상태 키는 환경과 인프라 수명 주기를 기준으로 나눈다. 다음은 버킷 이름을 환경별 백엔드 설정으로 받는 예다. Terraform 1.10 이상에서 S3 잠금 파일을 쓸 수 있으며, 기존 DynamoDB 기반 잠금은 현재 공식 문서에서 사용 중단 예정으로 표시된다. [Terraform S3 Backend](https://developer.hashicorp.com/terraform/language/backend/s3)

```hcl
terraform {
  required_version = ">= 1.10.0, < 2.0.0"

  backend "s3" {
    key          = "network/dev/terraform.tfstate"
    region       = "ap-northeast-2"
    encrypt      = true
    use_lockfile = true
  }
}
```

백엔드 블록은 일반 Terraform 입력 변수나 로컬 값을 참조하지 않는다. 비밀이 아닌 버킷 이름은 초기화 설정으로 받고, 자격 증명은 프로파일·역할·환경 변수로 공급한다. S3 버전 관리로 복구 가능성을 확보하며, 상태와 잠금 파일의 접근 범위를 구분한다. 잠금 파일에는 생성·읽기·삭제 권한이 필요하다. 이미 관리하던 로컬 상태를 옮길 때는 현재 상태를 보호하고 대상 버킷과 키를 확인한 뒤 `terraform init -migrate-state`를 실행한다. `-reconfigure`는 기존 상태를 이관하지 않고 백엔드 설정을 다시 잡는 옵션이다. [Terraform Init](https://developer.hashicorp.com/terraform/cli/commands/init)

처음 연결할 때는 미리 준비한 버킷 이름을 `TF_STATE_BUCKET` 환경 변수에 설정하고 `terraform init -backend-config="bucket=$TF_STATE_BUCKET"`을 실행한다. 로컬 상태를 이관할 때도 같은 버킷 인수를 전달한다.

## 2. 변수, 함수, 안정적인 주소

아래는 AWS 계정 없이 평가할 수 있는 변수·함수 예제다. 별도의 로컬 구성에 두면 S3 백엔드 없이 실행할 수 있다. `cidrsubnet`은 `/16` 네트워크를 `/24`로 나누고 마지막 인수로 서브넷 번호를 고른다.

```hcl
variable "environment" {
  type    = string
  default = "dev"

  validation {
    condition     = contains(["dev", "stage"], var.environment)
    error_message = "environment must be dev or stage."
  }
}

locals {
  networks = {
    dev   = "10.20.0.0/16"
    stage = "10.30.0.0/16"
  }
  subnets = {
    for name, number in { public = 1, private = 11 } :
    name => cidrsubnet(local.networks[var.environment], 8, number)
  }
}

resource "terraform_data" "subnet" {
  for_each = local.subnets
  input    = merge({ environment = var.environment }, { name = each.key, cidr = each.value })
}

output "subnet_cidrs" {
  value = local.subnets
}
```

예를 들어 `stage`의 `private`은 `10.30.11.0/24`다. `for_each`에서 논리 키를 유지하면 목록 순서가 바뀌어도 리소스 주소가 안정적이다. 키를 바꾸는 작업은 실제 객체의 교체 계획과 구분해 `moved`로 주소 이전을 선언할 수 있다. [cidrsubnet](https://developer.hashicorp.com/terraform/language/functions/cidrsubnet) · [for_each](https://developer.hashicorp.com/terraform/language/meta-arguments/for_each) · [Module Refactoring](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring)

## 3. GitHub 변경 흐름

PR에서 `terraform fmt -check`와 `validate`를 실행하고, 권한 있는 경로에서 환경별 `plan`을 검토한다. 병합 후 동일 환경의 적용이 겹치지 않도록 잠금과 실행 직렬화를 함께 사용한다. 계획을 보관한다면 상태와 마찬가지로 접근을 제한한다. Git에는 `.tf`와 `.terraform.lock.hcl`, 공유가 의도된 비밀 없는 변수 설정만 올린다. 상태 파일, 저장된 plan, `.terraform/`와 평문 자격 증명은 저장소 밖에서 관리한다. [Terraform Dependency Lock File](https://developer.hashicorp.com/terraform/language/files/dependency-lock)

GitHub Actions에서 AWS 권한이 필요하면 OIDC로 단기 역할을 사용하고, 신뢰 범위를 저장소와 브랜치 또는 환경으로 제한한다. 승인받지 않은 PR의 코드가 적용 역할로 실행되지 않도록 계획·적용 경계를 둔다. [GitHub Actions · AWS OIDC](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
