"""
title: Photo Editor
author: PhotoAgent
description: 사진의 노출, 대비, 채도, 선명도, 화이트밸런스, 톤커브, 비네팅, 노이즈 제거 등 종합 보정을 수행하는 도구입니다. 보정 전/후 비교 이미지를 생성하고 다운로드 링크를 제공합니다.
requirements: pillow, numpy, opencv-python-headless
version: 1.0.0
"""

import base64
import io
import json
import os
import re
import time
import uuid
from typing import Optional

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False


class Tools:
    """사진 보정 도구 - 다양한 보정 파라미터를 적용하여 이미지를 개선합니다."""

    # 보정된 이미지 저장 경로 (OpenWebUI 컨테이너 우선, 없으면 로컬 디렉토리)
    DEFAULT_OPENWEBUI_DIR = "/app/backend/data/uploads/photo_editor"
    FALLBACK_DIR = os.path.join(os.getcwd(), "uploads", "photo_editor")

    def __init__(self):
        try:
            if os.path.exists("/app/backend/data/uploads") or os.access("/app", os.W_OK):
                self.SAVE_DIR = self.DEFAULT_OPENWEBUI_DIR
            else:
                self.SAVE_DIR = self.FALLBACK_DIR
            os.makedirs(self.SAVE_DIR, exist_ok=True)
        except Exception:
            self.SAVE_DIR = self.FALLBACK_DIR
            os.makedirs(self.SAVE_DIR, exist_ok=True)

    async def edit_photo(
        self,
        image_url: str,
        brightness: int = 0,
        contrast: int = 0,
        saturation: int = 0,
        sharpness: int = 0,
        temperature: int = 0,
        tint: int = 0,
        highlights: int = 0,
        shadows: int = 0,
        whites: int = 0,
        blacks: int = 0,
        clarity: int = 0,
        vibrance: int = 0,
        denoise: int = 0,
        vignette: int = 0,
        grain: int = 0,
        __event_emitter__=None,
    ) -> str:
        """
        사진에 다양한 보정을 적용합니다. 각 파라미터는 -100 ~ +100 범위입니다 (0 = 변경 없음).
        보정 전/후 비교 이미지와 다운로드 링크를 제공합니다.

        :param image_url: 보정할 이미지의 URL 또는 data URL
        :param brightness: 밝기 조정 (-100~100, 0=변경없음)
        :param contrast: 대비 조정 (-100~100, 0=변경없음)
        :param saturation: 채도 조정 (-100~100, 0=변경없음)
        :param sharpness: 선명도 조정 (0~100)
        :param temperature: 색온도 조정 (-100=차가움, 100=따뜻함)
        :param tint: 틴트 조정 (-100=그린, 100=마젠타)
        :param highlights: 하이라이트 조정 (-100~100)
        :param shadows: 섀도우 조정 (-100~100)
        :param whites: 화이트 포인트 조정 (-100~100)
        :param blacks: 블랙 포인트 조정 (-100~100)
        :param clarity: 선명감/텍스처 강조 (0~100)
        :param vibrance: 자연스러운 채도 증가 (-100~100)
        :param denoise: 노이즈 제거 강도 (0~100)
        :param vignette: 비네팅 효과 (0~100)
        :param grain: 필름 그레인 효과 (0~100)
        :return: 보정 전/후 비교 이미지 및 다운로드 링크
        """
        try:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "🎨 사진 보정을 시작합니다...",
                            "done": False,
                        },
                    }
                )

            # 이미지 로드
            img = self._load_image(image_url)
            if img is None:
                return "❌ 이미지를 로드할 수 없습니다."

            original = img.copy()
            img_rgb = img.convert("RGB")

            # 적용된 보정 목록 추적
            applied_edits = []

            # === 기본 보정 ===

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "☀️ 노출/밝기 보정 중...",
                            "done": False,
                        },
                    }
                )

            # 1. 밝기 보정
            if brightness != 0:
                factor = 1 + brightness / 100
                enhancer = ImageEnhance.Brightness(img_rgb)
                img_rgb = enhancer.enhance(factor)
                applied_edits.append(f"밝기: {brightness:+d}")

            # 2. 대비 보정
            if contrast != 0:
                factor = 1 + contrast / 100
                enhancer = ImageEnhance.Contrast(img_rgb)
                img_rgb = enhancer.enhance(factor)
                applied_edits.append(f"대비: {contrast:+d}")

            # 3. 화이트밸런스 (색온도 + 틴트)
            if temperature != 0 or tint != 0:
                img_array = np.array(img_rgb, dtype=np.float32)
                if temperature != 0:
                    # 따뜻함: R 증가, B 감소 / 차가움: R 감소, B 증가
                    temp_shift = temperature / 100.0 * 30
                    img_array[:, :, 0] = np.clip(
                        img_array[:, :, 0] + temp_shift, 0, 255
                    )
                    img_array[:, :, 2] = np.clip(
                        img_array[:, :, 2] - temp_shift, 0, 255
                    )
                    applied_edits.append(f"색온도: {temperature:+d}")

                if tint != 0:
                    # 마젠타: G 감소 / 그린: G 증가
                    tint_shift = tint / 100.0 * 20
                    img_array[:, :, 1] = np.clip(
                        img_array[:, :, 1] - tint_shift, 0, 255
                    )
                    applied_edits.append(f"틴트: {tint:+d}")

                img_rgb = Image.fromarray(img_array.astype(np.uint8))

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "🎚️ 톤 조정 중...",
                            "done": False,
                        },
                    }
                )

            # 4. 하이라이트/섀도우/화이트/블랙 조정
            if any([highlights, shadows, whites, blacks]):
                img_array = np.array(img_rgb, dtype=np.float32)
                luminance = (
                    0.299 * img_array[:, :, 0]
                    + 0.587 * img_array[:, :, 1]
                    + 0.114 * img_array[:, :, 2]
                )

                if highlights != 0:
                    # 밝은 영역 (>180) 에 적용
                    mask = np.clip((luminance - 180) / 75, 0, 1)
                    adjustment = highlights / 100.0 * 40
                    for c in range(3):
                        img_array[:, :, c] += mask * adjustment
                    applied_edits.append(f"하이라이트: {highlights:+d}")

                if shadows != 0:
                    # 어두운 영역 (<80) 에 적용
                    mask = np.clip((80 - luminance) / 80, 0, 1)
                    adjustment = shadows / 100.0 * 40
                    for c in range(3):
                        img_array[:, :, c] += mask * adjustment
                    applied_edits.append(f"섀도우: {shadows:+d}")

                if whites != 0:
                    # 가장 밝은 영역 (>220) 클리핑 포인트 조정
                    mask = np.clip((luminance - 220) / 35, 0, 1)
                    adjustment = whites / 100.0 * 30
                    for c in range(3):
                        img_array[:, :, c] += mask * adjustment
                    applied_edits.append(f"화이트: {whites:+d}")

                if blacks != 0:
                    # 가장 어두운 영역 (<30) 클리핑 포인트 조정
                    mask = np.clip((30 - luminance) / 30, 0, 1)
                    adjustment = blacks / 100.0 * 30
                    for c in range(3):
                        img_array[:, :, c] += mask * adjustment
                    applied_edits.append(f"블랙: {blacks:+d}")

                img_rgb = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))

            # 5. 채도 보정
            if saturation != 0:
                factor = 1 + saturation / 100
                enhancer = ImageEnhance.Color(img_rgb)
                img_rgb = enhancer.enhance(factor)
                applied_edits.append(f"채도: {saturation:+d}")

            # 6. Vibrance (자연스러운 채도 - 이미 포화된 색은 덜 영향)
            if vibrance != 0:
                if HAS_CV2:
                    img_array = np.array(img_rgb, dtype=np.float32)
                    hsv = cv2.cvtColor(img_array.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(
                        np.float32
                    )
                    sat_factor = 1 - (hsv[:, :, 1] / 255.0)
                    adjustment = vibrance / 100.0 * 40
                    hsv[:, :, 1] = np.clip(
                        hsv[:, :, 1] + sat_factor * adjustment, 0, 255
                    )
                    img_array = cv2.cvtColor(
                        hsv.astype(np.uint8), cv2.COLOR_HSV2RGB
                    )
                    img_rgb = Image.fromarray(img_array)
                else:
                    # Pillow HSV fallback
                    hsv_img = img_rgb.convert("HSV")
                    hsv_array = np.array(hsv_img, dtype=np.float32)
                    sat_factor = 1 - (hsv_array[:, :, 1] / 255.0)
                    adjustment = vibrance / 100.0 * 40
                    hsv_array[:, :, 1] = np.clip(
                        hsv_array[:, :, 1] + sat_factor * adjustment, 0, 255
                    )
                    img_rgb = Image.fromarray(
                        hsv_array.astype(np.uint8), mode="HSV"
                    ).convert("RGB")
                applied_edits.append(f"바이브런스: {vibrance:+d}")

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "✨ 세부 조정 중...",
                            "done": False,
                        },
                    }
                )

            # === 고급 보정 ===

            # 7. 선명도 (Sharpness)
            if sharpness > 0:
                factor = 1 + sharpness / 50
                enhancer = ImageEnhance.Sharpness(img_rgb)
                img_rgb = enhancer.enhance(factor)
                applied_edits.append(f"선명도: +{sharpness}")

            # 8. Clarity (로컬 대비 향상)
            if clarity > 0:
                img_array = np.array(img_rgb, dtype=np.float32)
                if HAS_CV2:
                    blurred = cv2.GaussianBlur(
                        img_array, (0, 0), sigmaX=10
                    )
                else:
                    # Pillow GaussianBlur fallback
                    blurred_img = img_rgb.filter(ImageFilter.GaussianBlur(radius=5))
                    blurred = np.array(blurred_img, dtype=np.float32)

                detail = img_array - blurred
                factor = clarity / 100.0 * 0.8
                img_array = np.clip(img_array + detail * factor, 0, 255)
                img_rgb = Image.fromarray(img_array.astype(np.uint8))
                applied_edits.append(f"선명감: +{clarity}")

            # 9. 노이즈 제거
            if denoise > 0:
                if HAS_CV2:
                    img_array = np.array(img_rgb)
                    h_value = denoise / 100.0 * 15
                    img_array = cv2.fastNlMeansDenoisingColored(
                        img_array, None, float(h_value), float(h_value), 7, 21
                    )
                    img_rgb = Image.fromarray(img_array)
                else:
                    # Pillow MedianFilter fallback
                    filter_size = 3 if denoise < 50 else 5
                    img_rgb = img_rgb.filter(ImageFilter.MedianFilter(size=filter_size))
                applied_edits.append(f"노이즈 제거: +{denoise}")

            # 10. 비네팅 효과
            if vignette > 0:
                img_array = np.array(img_rgb, dtype=np.float32)
                h, w = img_array.shape[:2]
                # 타원형 비네팅 마스크 생성
                Y, X = np.ogrid[:h, :w]
                center_y, center_x = h / 2, w / 2
                distances = np.sqrt(
                    ((X - center_x) / (w / 2)) ** 2 + ((Y - center_y) / (h / 2)) ** 2
                )
                vignette_mask = 1 - np.clip(distances - 0.5, 0, 1) * (
                    vignette / 100.0 * 0.8
                )
                for c in range(3):
                    img_array[:, :, c] *= vignette_mask
                img_rgb = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
                applied_edits.append(f"비네팅: +{vignette}")

            # 11. 필름 그레인 효과
            if grain > 0:
                img_array = np.array(img_rgb, dtype=np.float32)
                noise = np.random.normal(0, grain / 100.0 * 20, img_array.shape)
                img_array = np.clip(img_array + noise, 0, 255)
                img_rgb = Image.fromarray(img_array.astype(np.uint8))
                applied_edits.append(f"그레인: +{grain}")

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "🖼️ 비교 이미지 생성 중...",
                            "done": False,
                        },
                    }
                )

            # === 결과 생성 ===

            # 비교 이미지 생성 (좌: 원본, 우: 보정)
            comparison = self._create_comparison(original.convert("RGB"), img_rgb)

            # 보정된 이미지 저장
            file_id = str(uuid.uuid4())[:8]
            timestamp = int(time.time())
            filename = f"edited_{timestamp}_{file_id}.jpg"
            filepath = os.path.join(self.SAVE_DIR, filename)

            img_rgb.save(filepath, "JPEG", quality=95)

            # Base64 인코딩
            comparison_b64 = self._image_to_base64(comparison)
            edited_b64 = self._image_to_base64(img_rgb)

            # 보정 파라미터 요약
            params = {
                "brightness": brightness,
                "contrast": contrast,
                "saturation": saturation,
                "sharpness": sharpness,
                "temperature": temperature,
                "tint": tint,
                "highlights": highlights,
                "shadows": shadows,
                "whites": whites,
                "blacks": blacks,
                "clarity": clarity,
                "vibrance": vibrance,
                "denoise": denoise,
                "vignette": vignette,
                "grain": grain,
            }
            # 0이 아닌 파라미터만 필터링
            active_params = {k: v for k, v in params.items() if v != 0}

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "✅ 사진 보정 완료!",
                            "done": True,
                        },
                    }
                )

            # 결과 반환
            result = f"## 🎨 사진 보정 완료!\n\n"
            result += f"### 적용된 보정\n"
            for edit in applied_edits:
                result += f"- {edit}\n"
            result += "\n"

            result += f"### 📊 보정 전/후 비교\n"
            result += f"![보정 비교](data:image/jpeg;base64,{comparison_b64})\n\n"

            result += f"### 📥 보정된 이미지\n"
            result += f"![보정 결과](data:image/jpeg;base64,{edited_b64})\n\n"

            result += f"💾 **저장 경로**: `{filepath}`\n"
            result += f"[📥 **보정된 사진 다운로드 (클릭)**](data:image/jpeg;base64,{edited_b64})\n\n"

            result += f"<details><summary>📋 보정 파라미터 (JSON)</summary>\n\n```json\n{json.dumps(active_params, ensure_ascii=False, indent=2)}\n```\n\n</details>"

            return result

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"❌ 보정 실패: {str(e)}",
                            "done": True,
                        },
                    }
                )
            return f"❌ 사진 보정 중 오류가 발생했습니다: {str(e)}"

    async def apply_preset(
        self,
        image_url: str,
        preset_name: str,
        intensity: int = 100,
        __event_emitter__=None,
    ) -> str:
        """
        사전 정의된 보정 프리셋을 적용합니다.

        :param image_url: 보정할 이미지의 URL
        :param preset_name: 프리셋 이름 (portrait, landscape, food, street, film_vintage, bright_airy, moody_dark, golden_hour, clean_natural)
        :param intensity: 프리셋 강도 (0~100, 기본 100)
        :return: 보정된 이미지
        """
        presets = {
            "portrait": {
                "brightness": 10,
                "contrast": 5,
                "saturation": -5,
                "sharpness": 15,
                "temperature": 5,
                "highlights": -15,
                "shadows": 20,
                "clarity": 10,
                "vibrance": 15,
                "vignette": 20,
            },
            "landscape": {
                "brightness": 5,
                "contrast": 20,
                "saturation": 20,
                "sharpness": 30,
                "temperature": -5,
                "highlights": -20,
                "shadows": 30,
                "clarity": 40,
                "vibrance": 25,
            },
            "food": {
                "brightness": 15,
                "contrast": 10,
                "saturation": 25,
                "sharpness": 20,
                "temperature": 15,
                "highlights": -10,
                "shadows": 15,
                "vibrance": 30,
                "vignette": 15,
            },
            "street": {
                "brightness": -5,
                "contrast": 30,
                "saturation": -10,
                "sharpness": 25,
                "clarity": 35,
                "vibrance": 10,
                "grain": 15,
            },
            "film_vintage": {
                "brightness": 5,
                "contrast": -10,
                "saturation": -20,
                "temperature": 15,
                "tint": 5,
                "highlights": -10,
                "shadows": 15,
                "blacks": 15,
                "grain": 30,
                "vignette": 35,
            },
            "bright_airy": {
                "brightness": 25,
                "contrast": -10,
                "saturation": -10,
                "temperature": 5,
                "highlights": 10,
                "shadows": 30,
                "whites": 15,
                "vibrance": 10,
            },
            "moody_dark": {
                "brightness": -20,
                "contrast": 25,
                "saturation": -15,
                "temperature": -10,
                "highlights": -30,
                "shadows": -10,
                "blacks": -20,
                "clarity": 30,
                "vignette": 45,
            },
            "golden_hour": {
                "brightness": 10,
                "contrast": 10,
                "saturation": 15,
                "temperature": 30,
                "tint": 5,
                "highlights": -15,
                "shadows": 25,
                "vibrance": 20,
                "vignette": 20,
            },
            "clean_natural": {
                "brightness": 5,
                "contrast": 5,
                "saturation": 5,
                "sharpness": 15,
                "highlights": -10,
                "shadows": 10,
                "clarity": 15,
                "vibrance": 10,
                "denoise": 5,
            },
        }

        if preset_name not in presets:
            available = ", ".join(presets.keys())
            return f"❌ 알 수 없는 프리셋입니다. 사용 가능한 프리셋: {available}"

        preset = presets[preset_name]

        # 강도 적용
        factor = intensity / 100.0
        adjusted_preset = {k: int(v * factor) for k, v in preset.items()}

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"🎨 '{preset_name}' 프리셋 적용 중 (강도: {intensity}%)...",
                        "done": False,
                    },
                }
            )

        # edit_photo 호출
        return await self.edit_photo(
            image_url=image_url,
            __event_emitter__=__event_emitter__,
            **adjusted_preset,
        )

    def _load_image(self, image_url: str) -> Optional[Image.Image]:
        """
        이미지 URL, Base64 data URL, 로컬 파일 경로 등 다양한 형태에서 이미지를 안전하게 로드합니다.
        """
        try:
            if not image_url or not isinstance(image_url, str):
                return None

            image_url = image_url.strip()

            # 마크다운 이미지 문법 처리: ![alt](url) -> url 추출
            md_match = re.search(r"!\[.*?\]\((.+?)\)", image_url)
            if md_match:
                image_url = md_match.group(1).strip()

            # HTML img 태그 처리: <img ... src="..." ...> -> src 추출
            html_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', image_url)
            if html_match:
                image_url = html_match.group(1).strip()

            # 따옴표 제거
            image_url = image_url.strip("\"'")

            # 1. Base64 Data URL 처리
            if image_url.startswith("data:image"):
                header, data = image_url.split(",", 1)
                image_data = base64.b64decode(data)
                return Image.open(io.BytesIO(image_data))

            # 2. 로컬 파일 시스템 직접 경로 확인
            if os.path.exists(image_url):
                return Image.open(image_url)

            # 3. OpenWebUI 컨테이너 내부 경로 및 상대 경로 탐색
            search_dirs = [
                "/app/backend/data/uploads",
                "/app/backend/data/uploads/photo_editor",
                "/app/backend/data/uploads/raw_processor",
                "./uploads",
                "./uploads/photo_editor",
            ]
            for sdir in search_dirs:
                candidate = os.path.join(sdir, os.path.basename(image_url))
                if os.path.exists(candidate):
                    return Image.open(candidate)

            # 4. OpenWebUI 상대 API URL 처리 (/api/v1/files/...)
            if image_url.startswith("/"):
                try:
                    import requests
                    internal_url = f"http://localhost:8080{image_url}"
                    response = requests.get(internal_url, timeout=10)
                    if response.status_code == 200:
                        return Image.open(io.BytesIO(response.content))
                except Exception:
                    pass

            # 5. 일반 HTTP/HTTPS URL 처리
            if image_url.startswith("http://") or image_url.startswith("https://"):
                import requests
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                return Image.open(io.BytesIO(response.content))

            # 6. 헤더 없는 순수 Base64 문자열 처리 시도
            try:
                raw_bytes = base64.b64decode(image_url)
                return Image.open(io.BytesIO(raw_bytes))
            except Exception:
                pass

            return None
        except Exception:
            return None

    def _create_comparison(
        self, original: Image.Image, edited: Image.Image
    ) -> Image.Image:
        """보정 전/후 비교 이미지를 생성합니다."""
        # 이미지 크기 통일
        max_width = 800
        if original.width > max_width:
            ratio = max_width / original.width
            new_size = (max_width, int(original.height * ratio))
            original = original.resize(new_size, Image.LANCZOS)
            edited = edited.resize(new_size, Image.LANCZOS)

        # 좌우 비교 이미지 생성
        gap = 4
        comparison_width = original.width * 2 + gap
        comparison = Image.new(
            "RGB", (comparison_width, original.height + 30), (40, 40, 40)
        )

        comparison.paste(original, (0, 30))
        comparison.paste(edited, (original.width + gap, 30))

        # 라벨 추가
        from PIL import ImageDraw

        draw = ImageDraw.Draw(comparison)
        draw.text((10, 5), "BEFORE (원본)", fill=(200, 200, 200))
        draw.text(
            (original.width + gap + 10, 5), "AFTER (보정)", fill=(100, 255, 100)
        )

        # 구분선
        draw.rectangle(
            [original.width, 0, original.width + gap, comparison.height],
            fill=(255, 255, 255),
        )

        return comparison

    def _image_to_base64(self, img: Image.Image) -> str:
        """이미지를 Base64 문자열로 변환합니다."""
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=90)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
