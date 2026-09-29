# 📷 RAW 파일 처리 베스트 프랙티스

## 1. RAW 파일이란?

### 정의
RAW 파일은 카메라 센서에서 캡처한 **처리되지 않은 원시 데이터**입니다. JPEG와 달리 카메라 내부에서 화이트밸런스, 샤프닝, 노이즈 제거, 톤 매핑 등의 처리가 적용되지 않습니다.

### RAW vs JPEG 비교
| 항목 | RAW | JPEG |
|------|-----|------|
| 비트 심도 | 12~16비트 (채널당) | 8비트 (채널당) |
| 압축 | 무손실 또는 최소 손실 | 유손실 압축 |
| 파일 크기 | 10~50+MB | 2~10MB |
| 후보정 여유 | 매우 넓음 (±3~4 EV) | 제한적 (±1 EV) |
| 화이트밸런스 | 후보정에서 자유롭게 변경 | 촬영 시 결정됨 |
| 색 공간 | 센서 네이티브 | sRGB 또는 Adobe RGB |
| 호환성 | 전용 소프트웨어 필요 | 어디서든 열림 |

## 2. 지원 RAW 형식

### Canon CR2 (Canon 5D)
- **구조**: TIFF 기반 컨테이너, 14비트 RAW 데이터
- **특성**: Bayer 패턴 (RGGB), Canon 고유 색 매트릭스
- **파일 크기**: 약 8~12MB (12.8MP)
- **주의**: 매우 오래된 형식이지만 rawpy/LibRaw에서 완벽히 지원

### Samsung DNG (Galaxy S26 Ultra Expert RAW)
- **구조**: Adobe DNG (Digital Negative) 표준 포맷
- **특성**: 16비트 리니어 데이터, 멀티프레임 합성 가능
- **파일 크기**: 약 25~50MB (200MP 메인 센서)
- **주의사항**:
  - 리니어 DNG이므로 감마 보정 없이 보면 매우 어두워 보임
  - `half_size=True` 사용 권장 (200MP 풀사이즈 처리는 매우 느림)
  - Samsung의 AI 노이즈 감소가 이미 적용되어 있을 수 있음

## 3. RAW 현상 워크플로우

### 단계별 프로세스

```
[1. RAW 읽기]
    ↓
[2. 화이트밸런스 적용]
    ↓
[3. 디모자이킹 (Demosaicing)]
    ↓
[4. 하이라이트 복구]
    ↓
[5. 색수차 보정]
    ↓
[6. 감마 보정]
    ↓
[7. 톤 매핑 / 자동 밝기]
    ↓
[8. 출력 (8/16비트 RGB)]
```

### 3.1 화이트밸런스 적용
```python
# 카메라 화이트밸런스 사용 (권장)
rgb = raw.postprocess(use_camera_wb=True)

# 일광 화이트밸런스
rgb = raw.postprocess(use_camera_wb=False)

# 카메라 WB가 부정확할 때: 자동 WB
# rawpy의 기본 자동 WB 사용
rgb = raw.postprocess(use_camera_wb=False, use_auto_wb=True)
```

### 3.2 하이라이트 복구 모드
| 모드 | 값 | 설명 | 추천 용도 |
|------|---|------|----------|
| Clip | 0 | 클리핑된 채널을 흰색으로 처리 | 기본값, 일반 용도 |
| Ignore | 1 | 클리핑 무시 | 색 정확도 우선 |
| Blend | 2 | 클리핑된 채널을 다른 채널 정보로 블렌드 | **추천**: 자연스러운 복구 |
| Reconstruct | 3 | 클리핑된 하이라이트를 재구성 | 하이라이트가 많이 날아간 경우 |

### 3.3 감마 설정
| 감마 | 값 | 설명 |
|------|---|------|
| sRGB | (2.222, 4.5) | 웹/모니터 표준, **기본 권장** |
| Linear | (1, 1) | 리니어 감마 (직접 톤 매핑할 때) |
| BT.709 | (2.222, 4.5) | 비디오 표준 (sRGB와 유사) |

### 3.4 기타 파라미터
- **half_size**: 절반 크기로 처리. 미리보기에 유용. Samsung 200MP에 필수.
- **no_auto_bright**: 자동 밝기 비활성화. 리니어 DNG를 직접 톤 매핑할 때 사용.
- **output_bps**: 8비트(표시용) 또는 16비트(추가 편집용)
- **chromatic_aberration**: 색수차 보정. Canon 5D의 오래된 렌즈에서 효과적.

## 4. 카메라별 추천 설정

### Canon 5D (CR2)
```json
{
    "use_camera_wb": true,
    "auto_brightness": true,
    "half_size": false,
    "output_bps": 8,
    "gamma": "srgb",
    "highlight_mode": 2,
    "chromatic_aberration": true,
    "output_format": "jpeg",
    "quality": 95
}
```

**이유**:
- Canon 5D는 12.8MP이므로 `half_size`는 불필요
- 오래된 렌즈의 색수차 보정 활성화
- 하이라이트 블렌드 모드로 자연스러운 복구
- 14비트 RAW → 8비트 출력 후 후보정

### Samsung Galaxy S26 Ultra (DNG)
```json
{
    "use_camera_wb": true,
    "auto_brightness": true,
    "half_size": true,
    "output_bps": 8,
    "gamma": "srgb",
    "highlight_mode": 0,
    "chromatic_aberration": false,
    "output_format": "jpeg",
    "quality": 95
}
```

**이유**:
- 200MP 원본은 처리 시간이 매우 오래 걸림 → `half_size=true`
- Samsung 렌즈의 색수차는 이미 카메라에서 보정됨
- 멀티프레임 합성으로 다이나믹 레인지가 넓어 기본 클립 모드 충분
- 16비트 리니어 → sRGB 감마 적용

## 5. 트러블슈팅

### 문제: RAW 현상 결과가 너무 어둡다
- **원인**: 리니어 DNG를 감마 보정 없이 처리
- **해결**: `gamma` 파라미터를 `srgb`로 설정

### 문제: 색이 원본 JPEG과 다르다
- **원인**: rawpy는 카메라 제조사의 ISP 알고리즘을 재현하지 않음
- **해결**: 정상적인 현상. `use_camera_wb=True`로 최대한 근접. 후보정으로 미세 조정.

### 문제: 처리 시간이 너무 오래 걸린다
- **원인**: 고해상도 RAW (특히 Samsung 200MP)
- **해결**: `half_size=True` 사용. 최종 출력만 풀사이즈로 처리.

### 문제: 파일을 열 수 없다
- **원인**: rawpy/LibRaw가 해당 RAW 형식을 지원하지 않음
- **해결**: rawpy와 LibRaw를 최신 버전으로 업데이트. `pip install --upgrade rawpy`

### 문제: 메모리 부족 (OOM)
- **원인**: 200MP 16비트 RAW 처리 시 대량의 메모리 필요 (약 1~2GB)
- **해결**: `half_size=True` 사용, Docker 컨테이너의 메모리 제한 확인

## 6. 품질 최대화를 위한 팁

1. **RAW → JPEG 변환 후 보정**: rawpy로 기본 현상 → Photo Editor 도구로 세밀한 보정
2. **16비트 중간 파일**: 추가 편집이 많을 경우 16비트 PNG로 중간 저장
3. **화이트밸런스 우선 조정**: 화이트밸런스가 틀리면 다른 보정이 무의미
4. **노출 보정 → 대비 → 색감 → 디테일 순서**: 큰 조정부터 작은 조정으로
5. **최종 출력은 JPEG 95%**: 품질과 파일 크기의 균형점
