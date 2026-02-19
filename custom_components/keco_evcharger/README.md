# KECO EV Charger (Home Assistant 커스텀 컴포넌트)

한국환경공단(KECO) 전기차 충전소 OpenAPI 연동 컴포넌트입니다.

## 설치
- 이 폴더(`custom_components/keco_evcharger`)를 Home Assistant의 `/config/custom_components/` 아래에 복사하세요.
- 또는 저장소 루트의 README에 있는 HACS 설치 절차를 따르세요.

## 초기 설정
1. Home Assistant → 설정 → 기기 및 서비스 → 통합 추가 → **KECO EV Charger**
2. 서비스키 입력
   - **Decoding(일반 인증키) 권장**
   - 발급: https://www.data.go.kr → `한국환경공단_전기자동차 충전소 정보` → 활용신청

## 항목 추가(충전소 등록)
1. 통합 상세 → 구성
2. **항목 추가(충전소 검색)** 선택
3. 충전소명/주소/운영사/충전소ID로 검색
4. 원하는 결과를 선택하여 `statId` 등록

## 엔티티 정책
- 기본 활성: 상태, 상태 갱신 시각, 현재 충전 시작 시각
- 기본 비활성: 상태 코드, 직전 충전 시작/종료 시각, 출력(kW)
  - 필요 시 엔티티 레지스트리에서 활성화

## 데이터 갱신 주기
- **5분 고정** (300초)
