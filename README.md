# 🌸 HouseholdAccountBook (스마트 파스텔 가계부)

> **PC와 스마트폰을 잇는 크로스 플랫폼 스마트 가계부 시스템**  
> Google 스프레드시트 템플릿(연간 대시보드 + 1~12월 월별 재무 관리)과 100% 호환되며, 파스텔톤 글라스모피즘(Glassmorphism) 모바일 UI를 탑재하여 누구나 3초 만에 일상 지출을 기록하고 자산을 관리할 수 있습니다.

---

## ✨ 핵심 기능

1. **📱 모바일 초간편 빠른 지출 등록 (Mobile-First Quick Entry)**
   - 스마트폰 기본 브라우저(Safari, Chrome, Samsung Internet 등)에서 별도 앱 설치 없이 접속
   - PWA(Progressive Web App) 지원으로 홈 화면에 앱처럼 추가 가능
   - 오늘 날짜 기본 선택, 원터치 카테고리 칩, 숫자 키패드 지원으로 3초 컷 지출 등록
   - 당일 지출 실시간 목록 및 당월 예산 소진 현황 요약 카드

2. **📊 PC 관리자 대시보드 (Admin & Annual Analytics)**
   - Google 스프레드시트의 `[연간 대시보드]`를 완벽 시각화한 인터랙티브 차트 (수입 vs 지출 vs 저축, 저축률 곡선)
   - 1월부터 12월까지 월별 세부 탭 제공
   - 고정 수입(기본급/상여), 고정 지출(관리비/통신비/보험료/대출), 저축 및 투자(적금/연금/주식) 템플릿 관리
   - 변동 지출 내역 엑셀식 일괄 편집/정렬/필터링

3. **🔄 Google 스프레드시트 100% 양방향 호환 (XLSX / CSV)**
   - 기존 구글 시트 파일(`.xlsx`) 드래그 앤 드롭으로 DB 즉시 로드
   - 언제든 클릭 한 번으로 원본 시트와 동일한 구조(연간 대시보드 + 1~12월 시트)의 엑셀 파일 내보내기

4. **💾 범용 데이터 포맷 & 무손실 복구 (Universal Portability)**
   - 무설치 단일 파일 데이터베이스 SQLite3 (`data/account_book.db`)
   - 컴퓨터를 교체하거나 OS를 재설치하더라도 `data/` 폴더만 복사하면 1초 만에 100% 복구
   - 매일 자동 롤링 백업 스냅샷 보관

5. **⚡ Zero-Config LAN 연결 & 콘솔 QR 코드**
   - 서버 시작 시 PC의 로컬 네트워크 IP(예: `192.168.0.15:8000`)를 자동 탐지
   - 터미널에 **아스키 QR 코드**를 출력하여 스마트폰 카메라로 비추면 바로 웹앱 진입

---

## 🎨 UI/UX 디자인 시스템 (Pastel & Glassmorphism)

- **컬러 팔레트**: 세이지 민트(#A8E6CF), 크림 피치(#FFD3B6), 파우더 블루(#BEE3F8), 버터 옐로우(#FFF3B0), 소프트 라벤더(#DED2F9), 베이비 로즈(#FFB7B2)
- **비주얼 효과**: 반투명 유리 블러 질감(`backdrop-filter: blur(16px)`), 소프트 글로우 섀도우, 부드러운 스퀴클 둥근 모서리

---

## 🚀 빠른 시작 가이드 (Quick Start)

### 1) Windows
```cmd
run_windows.bat
```
- 파이썬 가상환경 자동 구성 및 필요한 패키지 자동 설치
- 모바일 접속용 QR 코드 출력 및 기본 브라우저 자동 오픈

### 2) macOS & Linux
```bash
chmod +x run_unix.sh
./run_unix.sh
```

### 3) Docker (홈서버 / NAS)
```bash
docker compose up -d
```

---

## 📁 프로젝트 구조

```
HouseholdAccountBook/
├── app/
│   ├── core/              # 서버 설정, 네트워크 감지, QR 유틸
│   ├── database/          # SQLite 연결 및 모델 정의
│   ├── services/          # 스프레드시트(XLSX) 임포트/익스포트, 재무 연산 로직
│   ├── routers/           # RESTful API 엔드포인트
│   └── static/            # 파스텔 글라스 프론트엔드 (HTML/CSS/JS/PWA)
├── data/                  # SQLite DB 및 자동 롤링 백업 저장소
├── docs/                  # 마스터 플랜 및 상세 설계 문서
├── tests/                 # 단위 및 통합 테스트
├── run_windows.bat        # Windows 원클릭 실행 스크립트
├── run_unix.sh            # Mac/Linux 실행 스크립트
├── docker-compose.yml     # Docker 구동 설정
├── requirements.txt       # 의존성 패키지 목록
└── README.md
```

---

## 📖 상세 설계 문서
프로젝트의 전체 아키텍처, ERD, API 명세, 스프레드시트 분석 결과 등은 [docs/MASTER_PLAN.md](file:///home/taejonggo/Projects/HouseholdAccountBook/docs/MASTER_PLAN.md)에서 확인하실 수 있습니다.
