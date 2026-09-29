# 📸 OpenWebUI PhotoAgent

OpenWebUI에서 Local LLM(Gemma 4 등)과 Vision 모델을 결합한 **전문가 수준의 대화형 AI 사진 보정 에이전트**입니다.

사용자가 사진을 업로드하면 AI가 EXIF 및 히스토그램을 정밀 분석하고, 대화를 통해 보정 방향을 논의한 후 실제 이미지 보정을 수행합니다.

> 💡 **전제 조건**: OpenWebUI와 Local LLM(LM Studio / Ollama 등)이 이미 정상 작동 중인 환경에서, 아래 파일들을 OpenWebUI 웹 화면에 등록하기만 하면 즉시 사용 가능합니다.

---

## 📂 프로젝트 구성 파일

OpenWebUI 웹 UI에 등록할 파일 목록입니다:

```text
OpenwebUI_PhotoAgent/
├── tools/                         # [Workspace > Tools] 에 등록할 도구 코드
│   ├── photo_analyzer.py          # 1. 사진 정밀 분석기 (EXIF, 히스토그램, 품질 점수)
│   ├── photo_editor.py            # 2. 사진 보정기 (15개 세부 파라미터 + 9개 프리셋)
│   └── raw_processor.py           # 3. RAW 현상기 (Canon CR2/CR3, Samsung DNG 등)
├── filters/                       # [Admin Panel > Functions] 에 등록할 필터 코드
│   └── photo_agent_filter.py      # 대화 흐름 제어 (이미지 자동 감지 및 가이드 주입)
├── knowledge/                     # [Workspace > Knowledge] 에 업로드할 지식 문서
│   ├── photo_editing_basics.md    # 사진 보정 기초 이론
│   ├── camera_profiles.md         # 카메라별 센서/색감 특성
│   ├── genre_style_guide.md       # 장르별 보정 스타일 가이드
│   └── raw_processing_guide.md    # RAW 파일 처리 가이드
├── prompts/                       # 모델 생성 시 사용할 프롬프트
│   └── system_prompt.md           # 사진 전문가 페르소나 시스템 프롬프트
├── test_agent.py                  # 로컬 사전 검증용 테스트 스크립트
└── architecture.md                # 시스템 아키텍처 상세 문서
```

---

## 🛠️ OpenWebUI 등록 가이드 (순서대로 따라하기)

### 1단계: 도구(Tools) 등록

OpenWebUI 상단/좌측 메뉴에서 **Workspace (작업 공간) → Tools (도구)** 로 이동한 뒤 우측 상단 **`+`** 버튼을 누릅니다.

아래 3개 파일의 내용을 각각 복사하여 붙여넣고 저장합니다:

| 도구 이름 | 소스 파일 위치 | 설명 |
| :--- | :--- | :--- |
| **Photo Analyzer** | `tools/photo_analyzer.py` | EXIF, RGB 히스토그램, 노출/화이트밸런스 분석 |
| **Photo Editor** | `tools/photo_editor.py` | 15개 파라미터 보정, 전/후 비교, 9개 프리셋, 다운로드 |
| **RAW Processor** | `tools/raw_processor.py` | Canon CR2, Samsung DNG 등 RAW 현상 |

> 📌 **참고**: 각 코드 상단에 `requirements:`가 포함되어 있어, OpenWebUI 저장 시 필요한 패키지가 자동 인식됩니다.

---

### 2단계: 필터(Filter) 등록

1. 좌측 하단 관리자 메뉴 → **Admin Panel (관리자 패널) → Functions (함수)** 로 이동합니다.
2. 우측 상단 **`+`** 버튼을 클릭합니다.
3. `filters/photo_agent_filter.py` 파일의 전체 내용을 복사하여 붙여넣습니다.
4. 함수 타입을 **Filter**로 선택하고 저장합니다.
5. 함수 목록에서 `PhotoAgent Filter`의 **활성화 스위치(ON)**를 켭니다.

---

### 3단계: 지식 베이스(Knowledge) 등록

1. **Workspace (작업 공간) → Knowledge (지식)** 로 이동하여 **`+`** 버튼을 누릅니다.
2. 이름: `사진 보정 가이드`  
   설명: `사진 보정 이론, 카메라 프로필, 장르별 스타일 가이드`
3. 생성된 지식 베이스 화면에 `knowledge/` 폴더 안의 **4개 마크다운 파일**을 드래그하여 업로드합니다:
   - `photo_editing_basics.md`
   - `camera_profiles.md`
   - `genre_style_guide.md`
   - `raw_processing_guide.md`

---

### 4단계: 전용 모델(Model) 생성 및 연결

1. **Workspace (작업 공간) → Models (모델)** 로 이동하여 **`+`** 버튼을 클릭합니다.
2. 모델 기본 정보를 입력합니다:
   - **이름**: `PhotoAgent (사진 보정 전문가)`
   - **기본 모델(Base Model)**: 현재 로컬에 연결된 Vision 지원 모델 (예: `gemma-4-26b-a3b` 등) 선택
3. **시스템 프롬프트 (System Prompt)**:
   - `prompts/system_prompt.md` 파일의 내용을 그대로 복사하여 붙여넣습니다.
4. **연동 설정**:
   - **Tools**: 등록한 3개 도구(`Photo Analyzer`, `Photo Editor`, `RAW Processor`) 체크 활성화
   - **Filters**: `PhotoAgent Filter` 체크 활성화
   - **Knowledge**: `사진 보정 가이드` 연결
5. 우측 하단 **저장(Save)**을 누릅니다.

---

### 5단계: 사용하기

1. OpenWebUI 새 채팅을 열고 방금 생성한 **`PhotoAgent`** 모델을 선택합니다.
2. 사진(JPEG, PNG 또는 RAW 파일)을 드래그하여 첨부하고 메시지를 보냅니다:
   > *"이 사진 분석하고 어울리는 스타일로 보정해줘"*
3. AI가 사진의 기술적 상태를 분석한 후 보정 방향을 제안하며, 사용자가 확인하면 보정된 이미지와 비교샷, 다운로드 링크를 제공합니다.

---

## 💬 대화 워크플로우 예시

```text
[사용자] 사진 첨부 + "색감이 어둡고 칙칙한데 화사하게 바꿔줘"
   │
   ▼
[PhotoAgent] 사진 분석기(analyze_photo) 자동 호출
   │  - 히스토그램 시각화 및 노출/화이트밸런스 분석
   │  - "평균 밝기가 85/255로 어둡고 색온도가 차가운 편입니다."
   │  - 제안:
   │    1안) 밝기 +20, 색온도 +15, 채도 +20
   │    2안) 'bright_airy' (밝고 투명한 감성 스냅) 프리셋
   ▼
[사용자] "2안으로 진행해줘"
   │
   ▼
[PhotoAgent] 보정기(apply_preset / edit_photo) 실행
   │  - [BEFORE / AFTER 비교 이미지] 렌더링
   │  - [보정된 고화질 결과 이미지] 렌더링
   │  - [📥 보정된 사진 다운로드 (클릭)] 링크 제공
   ▼
[사용자] 만족 시 다운로드 / 필요시 "채도만 살짝 더 올려줘" 등 미세 조정 가능
```

---

## 🎨 지원하는 보정 기능 및 프리셋

### 세부 보정 파라미터 (-100 ~ +100)
- **노출/대비**: `brightness` (밝기), `contrast` (대비), `highlights` (하이라이트), `shadows` (섀도우), `whites` (화이트), `blacks` (블랙)
- **색감/화이트밸런스**: `temperature` (색온도), `tint` (틴트), `saturation` (채도), `vibrance` (자연스러운 채도)
- **디테일/특수효과**: `sharpness` (선명도), `clarity` (선명감), `denoise` (노이즈 제거), `vignette` (비네팅), `grain` (필름 그레인)

### 9가지 스타일 프리셋 (`apply_preset`)
1. `portrait`: 인물 사진 (부드럽고 자연스러운 피부 톤, 밝은 섀도우)
2. `landscape`: 풍경 사진 (깊은 대비, 선명한 하늘/자연 채도)
3. `food`: 음식 사진 (따뜻한 색온도, 생동감 있는 채도)
4. `street`: 거리/스냅 (강한 대비, 명암 표현, 미세한 텍스처)
5. `film_vintage`: 레트로 필름 (바랜 톤, 그레인, 비네팅 감성)
6. `bright_airy`: 밝고 투명한 스냅 (높은 노출, 부드러운 하이라이트)
7. `moody_dark`: 차분하고 묵직한 분위기 (어두운 노출, 높은 대비)
8. `golden_hour`: 노을/일몰 (따뜻한 황금빛 오렌지 톤)
9. `clean_natural`: 정갈한 기본 보정 (과하지 않은 깔끔한 톤 정리)

---

## 🧪 (선택 사항) 로컬 기능 테스트

OpenWebUI에 코드를 등록하기 전, 내 컴퓨터 로컬 환경에서 도구와 필터가 잘 동작하는지 미리 테스트해보고 싶다면 아래 명령어로 실행할 수 있습니다:

```bash
python test_agent.py
```
*(합성 테스트 이미지를 자동 생성하여 분석, 개별 보정, 프리셋 보정, 필터 동작을 한 번에 검증합니다)*
