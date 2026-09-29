# 📸 OpenWebUI PhotoAgent

OpenWebUI에서 Local LLM(Gemma 4 등)과 Vision 모델을 결합한 **전문가 수준의 대화형 AI 사진 보정 시스템**입니다.

사용자가 사진을 업로드하면 AI가 EXIF 및 히스토그램을 정밀 분석하고, 사용자와 대화하며 보정 방향을 잡은 후 실제 이미지 보정을 수행합니다.

---

## 🏗️ 프로젝트 구조

```text
OpenwebUI_PhotoAgent/
├── tools/
│   ├── photo_analyzer.py      # 사진 분석 도구 (EXIF, 히스토그램, 품질/색상 분석)
│   ├── photo_editor.py        # 사진 보정 도구 (15개 파라미터 + 9개 감성 프리셋)
│   └── raw_processor.py       # RAW 파일 현상 도구 (Canon CR2/CR3, Samsung DNG 등)
├── filters/
│   └── photo_agent_filter.py  # 대화 흐름/상태 제어 필터 (Inlet/Outlet)
├── knowledge/
│   ├── photo_editing_basics.md       # 사진 보정 기초 이론 (노출, WB, 톤)
│   ├── camera_profiles.md            # Canon 5D / Samsung S26 Ultra 카메라 프로필
│   ├── genre_style_guide.md          # 인물/풍경/음식/스트리트 스타일 가이드
│   └── raw_processing_guide.md       # RAW 파일 처리 베스트 프랙티스
├── prompts/
│   └── system_prompt.md              # 사진 전문가 페르소나 시스템 프롬프트
├── docker-compose.yml         # 원클릭 OpenWebUI + 호스트 LM Studio 연동
├── Dockerfile.custom          # 이미지/RAW 처리 라이브러리가 사전 빌드된 컨테이너
├── requirements.txt           # 파이썬 의존성 패키지 명세
├── test_agent.py              # 로컬 종합 단위 테스트 스크립트
├── architecture.md            # 시스템 아키텍처 및 시퀀스 다이어그램
└── README.md
```

---

## 🚀 빠른 시작 (Docker Compose)

OpenWebUI와 필수 이미지 처리 라이브러리(`rawpy`, `opencv`, `pillow` 등)를 한 번에 빌드하고 실행할 수 있습니다.

```bash
# 1. 컨테이너 빌드 및 백그라운드 실행
docker compose up -d --build

# 2. 브라우저에서 OpenWebUI 접속
# http://localhost:8080
```

> **LM Studio 연동 안내**:
> `docker-compose.yml`에 `host.docker.internal:host-gateway` 설정이 포함되어 있어, 호스트 머신에서 LM Studio 서버(포트 1234)를 시작하면 OpenWebUI가 자동으로 감지합니다.

---

## 🧪 로컬 기능 검증 (단위 테스트)

OpenWebUI에 등록하기 전, 로컬 환경에서 도구와 필터 동작을 검증할 수 있습니다:

```bash
python test_agent.py
```

- **테스트 항목**:
  1. 합성 이미지(Data URL) 자동 생성
  2. `Photo Analyzer`: EXIF, 히스토그램 Base64 이미지, 종합 품질 점수 산출
  3. `Photo Editor`: 15가지 개별 파라미터 보정 및 전/후 비교 이미지 생성
  4. `Photo Editor`: `clean_natural` 프리셋 일괄 적용
  5. `PhotoAgent Filter`: 사용자 이미지 감지 시 워크플로우 컨텍스트 자동 주입(Inlet) 및 후속 옵션 안내(Outlet)

---

## 📋 OpenWebUI 설정 가이드

### 1단계: Tool 등록

1. OpenWebUI → **Workspace (작업 공간) → Tools (도구)** → **+** 버튼 클릭
2. 다음 파일들의 내용을 각각 복사하여 붙여넣고 저장합니다:
   - `tools/photo_analyzer.py`
   - `tools/photo_editor.py`
   - `tools/raw_processor.py`
3. 최신 OpenWebUI 사양에 맞춘 도구 함수와 UI 진행 상태(`__event_emitter__`)가 적용되어 있습니다.

### 2단계: Filter 등록

1. OpenWebUI → **Admin Panel (관리자 패널) → Functions (함수)** → **+** 버튼 클릭
2. `filters/photo_agent_filter.py` 내용을 붙여넣고 Type을 **Filter**로 선택
3. 저장 후 활성화 스위치를 켭니다.

### 3단계: Knowledge Base 생성

1. OpenWebUI → **Workspace → Knowledge (지식)** → **+** 버튼 클릭
2. 이름: `사진 보정 가이드` / 설명: `사진 보정 이론, 카메라 프로필, 장르별 스타일 가이드`
3. `knowledge/` 폴더의 4개 파일(`.md`)을 업로드합니다.

### 4단계: 전용 보정 모델 생성/설정

1. OpenWebUI → **Workspace → Models (모델)** → **+** (또는 기존 Gemma 4 모델 편집)
2. **Name**: `PhotoAgent (사진 보정 전문가)`
3. **Base Model**: LM Studio의 `gemma-4-26b-a3b` (Vision 지원 모델) 선택
4. **System Prompt**: `prompts/system_prompt.md` 내용 붙여넣기
5. **Tools**: 등록한 3개 도구(`Photo Analyzer`, `Photo Editor`, `RAW Processor`) 모두 체크 활성화
6. **Filters**: `PhotoAgent Filter` 체크 활성화
7. **Knowledge**: `사진 보정 가이드` 연결
8. 저장(Save)

---

## 💬 대화 및 사용 예시

### 일반 사진 보정 시나리오
1. **사용자**: 카페에서 찍은 사진 첨부 + *"이 사진 색감이 좀 칙칙한데 예쁘게 보정해줄래?"*
2. **AI (PhotoAgent)**:
   - 자동으로 `analyze_photo` 도구 호출
   - 히스토그램 및 노출/화이트밸런스 분석 결과 보고:
     > "평균 밝기가 85/255로 약간 어둡고, 색온도가 푸른 톤으로 치우쳐 있습니다. 채도도 낮아 음료의 생동감이 부족합니다."
   - 추천 방향 제시:
     > "1. 자연스러운 보정: 밝기 +20, 색온도 +15, 채도 +20, 선명도 +25  
     >  2. `food` 프리셋 적용: 음식 전용 따뜻하고 화사한 톤  
     >  어떤 방향으로 진행할까요?"
3. **사용자**: *"1번 추천대로 해줘"*
4. **AI**:
   - `edit_photo` 도구 호출하여 보정 수행
   - **BEFORE / AFTER 비교 이미지** 및 **보정된 고화질 사진**, **원클릭 다운로드 링크** 제공

### RAW 파일 현상 시나리오
1. **사용자**: Canon CR2 또는 Samsung DNG 파일 첨부 + *"이 RAW 사진 현상해줘"*
2. **AI**:
   - `get_raw_info`로 센서 및 카메라 메타데이터 확인
   - `process_raw`로 16bit 톤 매핑 및 카메라 화이트밸런스 적용 현상
   - 현상된 이미지를 대상으로 `analyze_photo` 후 2차 정밀 보정 진행

---

## 🎨 주요 보정 파라미터 및 프리셋

### 세부 조정 파라미터 (-100 ~ +100)
- **기본 노출/색상**: `brightness`, `contrast`, `saturation`, `vibrance`
- **화이트밸런스**: `temperature` (색온도), `tint` (틴트)
- **톤 조절**: `highlights`, `shadows`, `whites`, `blacks`
- **디테일/효과**: `sharpness`, `clarity`, `denoise`, `vignette`, `grain`

### 9가지 스타일 프리셋 (`apply_preset`)
- `portrait` (화사하고 부드러운 피부 톤)
- `landscape` (깊은 대비와 푸른 하늘, 풍부한 채도)
- `food` (따뜻한 색온도와 선명한 색감)
- `street` (강한 대비와 텍스처, 미세한 그레인)
- `film_vintage` (바랜 느낌의 필름 감성)
- `bright_airy` (밝고 투명한 일본 감성 스냅)
- `moody_dark` (차분하고 묵직한 시네마틱 톤)
- `golden_hour` (노을빛 따스한 골든아워)
- `clean_natural` (군더더기 없는 정갈하고 자연스러운 보정)
