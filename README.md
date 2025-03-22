# 폴센트 코딩 테스트

## 프로젝트 소개

> 여기에 작성된 코드들은 다음과 같은 환경에서 작성되었음을 알려드립니다.  
> - IDE: Curosr
>   - AI의 도움을 받아 코드를 작성했습니다.
>   - claude-3.7-sonnet 모델을 사용하였습니다.
>   - Agent와 MCP를 최대한 활용하였습니다.

이 프로젝트는 쿠팡 상품 크롤링과 인스타그램 릴스 조회수 추출을 위한 두 가지 주요 기능을 포함하고 있습니다.

- [문제 보기](./TEST.md)

- [삽질 보기](./TROUBLE_SHOOTING.md)


## 설치 방법

```bash
# Poetry를 이용한 의존성 설치
poetry install

# 가상 환경 실행
poetry shell
```

## 기능 설명

### 1. 쿠팡 상품 크롤링 (coupang_product)
- 20개의 쿠팡 상품 URL을 크롤링하여 상품 정보 수집
- 성공률을 높이기 위한 다양한 기술 적용:
  - User-Agent 무작위 변경
  - 요청 간 랜덤 지연 시간 적용 (2-5초 기본, 설정에 따라 지연 시간 증가)
  - 여러 세션 사용으로 IP 분산 시뮬레이션
  - HTTP 요청에 대한 재시도 전략 적용 (5회 재시도, 백오프 전략 사용)
  - 다양한 HTTP 헤더 설정 및 랜덤화

### 2. 인스타그램 릴스 조회수 추출 (instagram_reels)
- 11개의 인스타그램 릴스 URL에서 조회수 정보 추출
- 다양한 클로링 방어 우회 기법 적용:
  - 모바일 및 데스크톱 User-Agent 랜덤 적용
  - GraphQL API 호출과 HTML 파싱 방식 병행
  - 요청 간 지연 시간 적용 (1-3초 기본, 설정에 따라 증가)
  - 다양한 레퍼러와 HTTP 헤더 사용

## 실행 방법

```bash
# 의존성 설치 (처음 한 번만)
poetry install

# 가상 환경에서 스크립트 실행
# v2 버전(기본값) 실행
poetry run python app/main.py coupang_product     # 쿠팡 상품 크롤링 실행 (v2)
poetry run python app/main.py instagram_reels     # 인스타그램 릴스 조회수 추출 실행 (v2)

# v1 버전 실행
poetry run python app/main.py coupang_product --version v1  # 쿠팡 상품 크롤링 v1 실행
poetry run python app/main.py instagram_reels --version v1  # 인스타그램 릴스 조회수 추출 v1 실행

# 또는 가상 환경 활성화 후 실행
poetry shell

# 가상 환경 셸에 진입한 후에는 다음과 같이 직접 실행 가능
python app/main.py coupang_product             # v2 버전(기본값)
python app/main.py instagram_reels             # v2 버전(기본값)
python app/main.py coupang_product --version v1 # v1 버전
python app/main.py instagram_reels --version v1 # v1 버전
```

## 설정 파일

### 인스타그램 릴스 설정 (configs/instagram.yaml)
```yaml
reels_urls:
  - "https://www.instagram.com/reel/DAiOanto5rM/?igsh=MW1yYnYzdWgwZ3VhNw=="
  - "https://www.instagram.com/reel/DAqSjKtS1Gl/?igsh=MTZuMHNwdDM1eThieg=="
  # ... 기타 URL 목록 (총 11개)

api_settings:
  query_hash: "b3055c01b4b222b8a47dc12b090e4e64"
  request_delay:
    min: 1
    max: 3
```

### 쿠팡 상품 설정 (configs/coupang.yaml)
```yaml
product_urls:
  - "https://www.coupang.com/vp/products/8134993903?itemId=23107127826&vendorItemId=90140409719&isAddedCart="
  - "https://www.coupang.com/vp/products/1402935103?itemId=2430415008&vendorItemId=70424371600&isAddedCart="
  # ... 기타 URL 목록 (총 20개)

request_settings:
  retry:
    total: 5
    status_forcelist: [429, 500, 502, 503, 504]
    backoff_factor: 2
  delay_range:
    min: 2
    max: 5
  sessions_count: 3
```

## 프로젝트 구조
```
프로젝트/
├── app/                        # 주요 애플리케이션 코드
│   ├── main.py                 # 애플리케이션의 진입점
│   ├── v1/                     # v1 버전 코드
│   │   ├── __init__.py         # 패키지 초기화 파일
│   │   ├── coupang_product.py  # 쿠팡 상품 크롤링 구현
│   │   └── instagram_reels.py  # 인스타그램 릴스 크롤링 구현
│   ├── v2/                     # v2 버전 코드
│   │   ├── __init__.py         # 패키지 초기화 파일
│   │   ├── coupang_product.py  # 쿠팡 상품 크롤링 구현 (v2)
│   │   └── instagram_reels.py  # 인스타그램 릴스 크롤링 구현 (v2)
├── configs/                    # 설정 파일
│   ├── coupang.yaml            # 쿠팡 크롤링 설정
│   ├── instagram.yaml          # 인스타그램 설정
├── pyproject.toml              # Poetry 의존성 관리
├── poetry.lock                 # 의존성 잠금 파일
└── README.md                   # README 파일
```

## 버전별 주요 차이점
- **v1**: 문제를 잘못된 방향으로 풀었음
- **v2**: 문제의 원래 의도대로 다시 작성

## 의존성 패키지
- Python 3.10 이상
- requests: HTTP 요청 처리
- fake-useragent: User-Agent 랜덤화
- urllib3: HTTP 클라이언트
- pyyaml: YAML 파일 처리
- beautifulsoup4: HTML 파싱

## 주의사항
- 크롤링은 해당 웹사이트의 이용약관을 준수하여 사용해야 합니다
- IP 차단을 방지하기 위해 적절한 지연 시간이 적용되어 있습니다
- 웹사이트 구조 변경 시 코드 업데이트가 필요할 수 있습니다 