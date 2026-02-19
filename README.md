# KECO EV Charger (Home Assistant 커스텀 컴포넌트)

한국환경공단(KECO) 전기차 충전소 OpenAPI를 이용해,
Home Assistant에서 충전소/충전기 상태를 모니터링하는 커스텀 컴포넌트입니다.

---

## 1) 프로젝트 구조

```text
ha-keco-evcharger/
├─ hacs.json
├─ LICENSE
├─ README.md
└─ custom_components/
   └─ keco_evcharger/
      ├─ __init__.py
      ├─ manifest.json
      ├─ const.py
      ├─ api.py
      ├─ coordinator.py
      ├─ config_flow.py
      ├─ sensor.py
      ├─ strings.json
      └─ translations/
         └─ ko.json
```

---

## 2) 설치 방법

### 방법 A. HACS 설치 (권장)

1. HACS → **Integrations** → 우측 상단 메뉴(⋮) → **Custom repositories**
2. 이 저장소 URL 추가
3. Category는 **Integration** 선택
4. 목록에서 **KECO EV Charger** 설치
5. Home Assistant 재시작

### 방법 B. 수동 설치

1. Home Assistant 설정 디렉토리의 `custom_components` 폴더로 이동
2. 이 저장소의 `custom_components/keco_evcharger` 폴더를 그대로 복사
3. Home Assistant 재시작

최종 경로 예시:

```text
/config/custom_components/keco_evcharger/
```

---

## 3) API 키 발급 방법 (공공데이터포털)

1. [https://www.data.go.kr](https://www.data.go.kr) 로그인
2. `한국환경공단_전기자동차 충전소 정보` 데이터 페이지 이동
3. **활용신청** 진행
4. 인증키(서비스키) 발급 후 복사

> **권장 입력값: Decoding(일반 인증키)**
> - 이 컴포넌트 입력란에는 **Decoding 키(일반 인증키)**를 넣는 것을 권장합니다.
> - Encoding 키를 넣어도 동작하는 경우가 있으나, 환경에 따라 인증 오류가 발생할 수 있습니다.

---

## 4) Home Assistant에서 설정

1. **설정 → 기기 및 서비스 → 통합 추가**
2. `KECO EV Charger` 선택
3. 서비스키 입력
4. 초기 등록 완료

---

## 5) 충전소 추가/제거

통합 상세 화면에서 옵션으로 관리합니다.

- **항목 추가(충전소 검색)**
  - 검색어(충전소명/주소/운영사/충전소ID) 입력
  - 검색 결과에서 원하는 충전소 선택
- **항목 제거**
  - 등록된 충전소 중 제거할 항목 선택

예: 원하는 충전소명 또는 주소로 검색 후 `statId` 항목 선택

---

## 6) 엔티티 정책

### 기본 활성 엔티티
- 상태 (한글 매핑)
- 상태 갱신 시각
- 현재 충전 시작 시각

### 기본 비활성 엔티티 (필요 시 활성화)
- 상태 코드
- 직전 충전 시작 시각
- 직전 충전 종료 시각
- 출력(kW)

> 상세 필드는 `entity_registry_enabled_default=False`로 등록되어,
> 필요할 때 HA에서 켜서 사용할 수 있습니다.

---

## 7) 데이터 갱신 주기

- **5분 고정** (300초)

---

## 8) 상태 코드 참고

- `1`: 통신이상
- `2`: 충전대기
- `3`: 충전중
- `4`: 운영중지
- `5`: 점검중
- `9`: 상태미확인

---

## 9) 주의사항

- 공공 API 특성상 특정 시점에 일부 충전소 데이터가 비거나 지연될 수 있습니다.
- 충전소/운영사별로 상태 갱신 빈도가 다를 수 있습니다.

---

## 10) 라이선스

MIT License (`LICENSE` 파일 참조)
