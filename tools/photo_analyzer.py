"""
title: Photo Analyzer
author: PhotoAgent
description: 사진의 EXIF 데이터, 히스토그램, 색온도, 노이즈 레벨 등을 종합 분석하여 보정 방향을 제안하는 도구입니다.
requirements: pillow, numpy, piexif
version: 1.0.0
"""

import base64
import io
import json
import math
import os
import re
import struct
from typing import Optional

import numpy as np
from PIL import Image, ImageStat
from PIL.ExifTags import TAGS, GPSTAGS


class Tools:
    """사진 분석 도구 - 이미지의 기술적 메타데이터와 품질을 분석합니다."""

    def __init__(self):
        pass

    async def analyze_photo(
        self,
        image_url: str,
        __event_emitter__=None,
    ) -> str:
        """
        업로드된 사진을 종합 분석합니다. EXIF 메타데이터, 히스토그램, 노출, 화이트밸런스, 노이즈 레벨 등을 분석하여 보정 방향을 제안합니다.
        :param image_url: 분석할 이미지의 URL 또는 data URL
        :return: JSON 형태의 종합 분석 리포트
        """
        try:
            # 상태 메시지 전송
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "📸 사진을 분석하는 중...",
                            "done": False,
                        },
                    }
                )

            # 이미지 로드
            img = self._load_image(image_url)
            if img is None:
                return json.dumps(
                    {"error": "이미지를 로드할 수 없습니다."}, ensure_ascii=False
                )

            # RGB로 변환
            img_rgb = img.convert("RGB")
            img_array = np.array(img_rgb)

            # 분석 실행
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "🔍 EXIF 데이터 추출 중...",
                            "done": False,
                        },
                    }
                )

            exif_data = self._extract_exif(img)

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "📊 히스토그램 분석 중...",
                            "done": False,
                        },
                    }
                )

            histogram_analysis = self._analyze_histogram(img_array)
            exposure_analysis = self._analyze_exposure(img_array)
            white_balance_analysis = self._analyze_white_balance(img_array)
            noise_analysis = self._analyze_noise(img_array)
            sharpness_analysis = self._analyze_sharpness(img_array)
            color_analysis = self._analyze_color(img_array)

            # 종합 품질 점수 계산
            quality_score = self._calculate_quality_score(
                exposure_analysis,
                white_balance_analysis,
                noise_analysis,
                sharpness_analysis,
                color_analysis,
            )

            # 보정 제안 생성
            suggestions = self._generate_suggestions(
                exposure_analysis,
                white_balance_analysis,
                noise_analysis,
                sharpness_analysis,
                color_analysis,
                histogram_analysis,
            )

            # 히스토그램 이미지 생성
            histogram_image = self._generate_histogram_image(img_array)

            # 결과 조합
            report = {
                "image_info": {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format or "Unknown",
                    "mode": img.mode,
                    "file_size_estimate": f"{len(img.tobytes()) / 1024 / 1024:.1f}MB",
                },
                "exif": exif_data,
                "histogram": histogram_analysis,
                "exposure": exposure_analysis,
                "white_balance": white_balance_analysis,
                "noise": noise_analysis,
                "sharpness": sharpness_analysis,
                "color": color_analysis,
                "quality_score": quality_score,
                "suggestions": suggestions,
            }

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "✅ 사진 분석 완료!",
                            "done": True,
                        },
                    }
                )

            # 히스토그램 이미지와 함께 반환
            result_text = f"## 📊 사진 분석 리포트\n\n"
            result_text += f"**이미지 정보**: {img.width}×{img.height} ({img.mode})\n\n"

            if exif_data:
                result_text += f"### 📷 카메라 정보\n"
                for key, value in exif_data.items():
                    result_text += f"- **{key}**: {value}\n"
                result_text += "\n"

            result_text += f"### 📈 히스토그램\n"
            result_text += f"![히스토그램]({histogram_image})\n\n"

            result_text += f"### 🎯 분석 결과\n"
            result_text += f"- **노출**: {exposure_analysis['status']} (평균 밝기: {exposure_analysis['mean_brightness']:.0f}/255)\n"
            result_text += f"- **화이트밸런스**: {white_balance_analysis['status']} (색온도 편향: {white_balance_analysis['color_temp_bias']})\n"
            result_text += f"- **노이즈**: {noise_analysis['status']} (레벨: {noise_analysis['level']:.2f})\n"
            result_text += f"- **선명도**: {sharpness_analysis['status']} (점수: {sharpness_analysis['score']:.0f})\n"
            result_text += f"- **채도**: {color_analysis['saturation_status']} (평균: {color_analysis['mean_saturation']:.0f})\n\n"

            result_text += f"### ⭐ 종합 품질 점수: {quality_score['total']}/100\n\n"

            result_text += f"### 💡 보정 제안\n"
            for i, suggestion in enumerate(suggestions, 1):
                priority_icon = "🔴" if suggestion['priority'] == 'high' else "🟡" if suggestion['priority'] == 'medium' else "🟢"
                result_text += f"{i}. {priority_icon} **{suggestion['category']}**: {suggestion['description']}\n"
                result_text += f"   - 추천값: `{suggestion['recommended_value']}`\n"

            # JSON 데이터도 함께 반환 (LLM이 도구 호출 시 참조할 수 있도록)
            result_text += f"\n\n<details><summary>📋 상세 분석 데이터 (JSON)</summary>\n\n```json\n{json.dumps(report, ensure_ascii=False, indent=2)}\n```\n\n</details>"

            return result_text

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"❌ 분석 실패: {str(e)}",
                            "done": True,
                        },
                    }
                )
            return json.dumps(
                {"error": f"분석 중 오류 발생: {str(e)}"}, ensure_ascii=False
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
                # OpenWebUI 내부 로컬호스트 엔드포인트 시도
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

    def _extract_exif(self, img: Image.Image) -> dict:
        """EXIF 메타데이터를 추출합니다."""
        exif_info = {}
        try:
            exif_raw = img._getexif()
            if exif_raw is None:
                return {"info": "EXIF 데이터가 없습니다"}

            # 주요 EXIF 태그 매핑
            tag_map = {
                "Make": "카메라 제조사",
                "Model": "카메라 모델",
                "ExposureTime": "셔터 속도",
                "FNumber": "조리개",
                "ISOSpeedRatings": "ISO",
                "FocalLength": "초점 거리",
                "WhiteBalance": "화이트밸런스",
                "Flash": "플래시",
                "MeteringMode": "측광 모드",
                "ExposureProgram": "촬영 모드",
                "LensModel": "렌즈",
                "DateTimeOriginal": "촬영 일시",
                "ExposureBiasValue": "노출 보정",
            }

            for tag_id, value in exif_raw.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                if tag_name in tag_map:
                    display_name = tag_map[tag_name]

                    # 값 포맷팅
                    if tag_name == "ExposureTime":
                        if isinstance(value, tuple):
                            value = f"{value[0]}/{value[1]}s"
                        elif value < 1:
                            value = f"1/{int(1/value)}s"
                        else:
                            value = f"{value}s"
                    elif tag_name == "FNumber":
                        if isinstance(value, tuple):
                            value = f"f/{value[0]/value[1]:.1f}"
                        else:
                            value = f"f/{value:.1f}"
                    elif tag_name == "FocalLength":
                        if isinstance(value, tuple):
                            value = f"{value[0]/value[1]:.0f}mm"
                        else:
                            value = f"{value:.0f}mm"
                    elif tag_name == "WhiteBalance":
                        wb_modes = {0: "자동", 1: "수동"}
                        value = wb_modes.get(value, str(value))
                    elif tag_name == "Flash":
                        value = "사용" if value & 1 else "미사용"

                    exif_info[display_name] = str(value)

        except Exception:
            exif_info["info"] = "EXIF 데이터 추출 실패"

        return exif_info

    def _analyze_histogram(self, img_array: np.ndarray) -> dict:
        """RGB 히스토그램을 분석합니다."""
        result = {}
        channels = {"red": 0, "green": 1, "blue": 2}

        for name, idx in channels.items():
            channel = img_array[:, :, idx].flatten()
            hist, _ = np.histogram(channel, bins=256, range=(0, 255))
            result[name] = {
                "mean": float(np.mean(channel)),
                "std": float(np.std(channel)),
                "median": float(np.median(channel)),
                "clipped_shadows": float(np.sum(channel < 5) / len(channel) * 100),
                "clipped_highlights": float(
                    np.sum(channel > 250) / len(channel) * 100
                ),
            }

        # 전체 밝기 (Luminance)
        luminance = (
            0.299 * img_array[:, :, 0]
            + 0.587 * img_array[:, :, 1]
            + 0.114 * img_array[:, :, 2]
        )
        result["luminance"] = {
            "mean": float(np.mean(luminance)),
            "std": float(np.std(luminance)),
            "dynamic_range": float(np.percentile(luminance, 99) - np.percentile(luminance, 1)),
        }

        return result

    def _analyze_exposure(self, img_array: np.ndarray) -> dict:
        """노출 상태를 분석합니다."""
        luminance = (
            0.299 * img_array[:, :, 0]
            + 0.587 * img_array[:, :, 1]
            + 0.114 * img_array[:, :, 2]
        )
        mean_brightness = float(np.mean(luminance))
        std_brightness = float(np.std(luminance))

        # 노출 판정
        if mean_brightness < 60:
            status = "언더노출 (어두움)"
            ev_correction = round((127 - mean_brightness) / 40, 1)
        elif mean_brightness > 200:
            status = "오버노출 (밝음)"
            ev_correction = round((127 - mean_brightness) / 40, 1)
        elif mean_brightness < 90:
            status = "약간 언더노출"
            ev_correction = round((127 - mean_brightness) / 60, 1)
        elif mean_brightness > 170:
            status = "약간 오버노출"
            ev_correction = round((127 - mean_brightness) / 60, 1)
        else:
            status = "적정 노출"
            ev_correction = 0.0

        # 하이라이트/섀도우 클리핑
        clipped_shadows = float(np.sum(luminance < 5) / luminance.size * 100)
        clipped_highlights = float(np.sum(luminance > 250) / luminance.size * 100)

        return {
            "status": status,
            "mean_brightness": mean_brightness,
            "std_brightness": std_brightness,
            "suggested_ev_correction": ev_correction,
            "clipped_shadows_pct": round(clipped_shadows, 2),
            "clipped_highlights_pct": round(clipped_highlights, 2),
            "contrast": "낮음" if std_brightness < 40 else "높음" if std_brightness > 80 else "적절",
        }

    def _analyze_white_balance(self, img_array: np.ndarray) -> dict:
        """화이트밸런스를 분석합니다."""
        r_mean = float(np.mean(img_array[:, :, 0]))
        g_mean = float(np.mean(img_array[:, :, 1]))
        b_mean = float(np.mean(img_array[:, :, 2]))

        # 색온도 편향 판정
        rg_ratio = r_mean / max(g_mean, 1)
        bg_ratio = b_mean / max(g_mean, 1)

        if rg_ratio > 1.15:
            color_temp_bias = "따뜻함 (오렌지/노란색 편향)"
            suggestion = "색온도를 낮추거나 파란색 틴트 추가"
        elif bg_ratio > 1.15:
            color_temp_bias = "차가움 (파란색 편향)"
            suggestion = "색온도를 높이거나 노란색 틴트 추가"
        elif rg_ratio > 1.05:
            color_temp_bias = "약간 따뜻함"
            suggestion = "미세 조정 필요"
        elif bg_ratio > 1.05:
            color_temp_bias = "약간 차가움"
            suggestion = "미세 조정 필요"
        else:
            color_temp_bias = "중립"
            suggestion = "화이트밸런스 양호"

        # 틴트 (마젠타-그린 축)
        mg_ratio = (r_mean + b_mean) / 2 / max(g_mean, 1)
        if mg_ratio > 1.1:
            tint = "마젠타 편향"
        elif mg_ratio < 0.9:
            tint = "그린 편향"
        else:
            tint = "중립"

        status = "양호" if color_temp_bias == "중립" and tint == "중립" else "조정 필요"

        return {
            "status": status,
            "color_temp_bias": color_temp_bias,
            "tint": tint,
            "r_mean": round(r_mean, 1),
            "g_mean": round(g_mean, 1),
            "b_mean": round(b_mean, 1),
            "rg_ratio": round(rg_ratio, 3),
            "bg_ratio": round(bg_ratio, 3),
            "suggestion": suggestion,
        }

    def _analyze_noise(self, img_array: np.ndarray) -> dict:
        """노이즈 레벨을 추정합니다."""
        # 라플라시안 기반 노이즈 추정
        gray = np.mean(img_array, axis=2)

        # 간단한 라플라시안 커널 적용
        h, w = gray.shape
        laplacian = np.zeros_like(gray)
        laplacian[1:-1, 1:-1] = (
            gray[:-2, 1:-1]
            + gray[2:, 1:-1]
            + gray[1:-1, :-2]
            + gray[1:-1, 2:]
            - 4 * gray[1:-1, 1:-1]
        )

        noise_level = float(np.std(laplacian)) / 255.0

        # 어두운 영역의 노이즈 (ISO 노이즈 특성)
        dark_mask = gray < 60
        if np.sum(dark_mask) > 100:
            dark_noise = float(np.std(gray[dark_mask]))
        else:
            dark_noise = 0.0

        if noise_level > 0.15:
            status = "높은 노이즈"
            denoise_strength = "강"
        elif noise_level > 0.08:
            status = "중간 노이즈"
            denoise_strength = "중"
        elif noise_level > 0.04:
            status = "약간의 노이즈"
            denoise_strength = "약"
        else:
            status = "깨끗"
            denoise_strength = "불필요"

        return {
            "status": status,
            "level": round(noise_level, 4),
            "dark_area_noise": round(dark_noise, 2),
            "suggested_denoise_strength": denoise_strength,
        }

    def _analyze_sharpness(self, img_array: np.ndarray) -> dict:
        """선명도를 분석합니다."""
        gray = np.mean(img_array, axis=2)

        # 라플라시안 분산으로 선명도 측정
        h, w = gray.shape
        laplacian = np.zeros_like(gray)
        laplacian[1:-1, 1:-1] = (
            gray[:-2, 1:-1]
            + gray[2:, 1:-1]
            + gray[1:-1, :-2]
            + gray[1:-1, 2:]
            - 4 * gray[1:-1, 1:-1]
        )

        sharpness_score = float(np.var(laplacian))

        if sharpness_score > 500:
            status = "매우 선명"
            suggestion = "불필요"
        elif sharpness_score > 200:
            status = "선명"
            suggestion = "약간의 샤프닝 가능"
        elif sharpness_score > 50:
            status = "보통"
            suggestion = "샤프닝 권장"
        else:
            status = "흐림"
            suggestion = "강한 샤프닝 필요 (모션 블러 또는 초점 이탈 의심)"

        return {
            "status": status,
            "score": round(sharpness_score, 1),
            "suggestion": suggestion,
        }

    def _analyze_color(self, img_array: np.ndarray) -> dict:
        """색상 분석 (채도, 색 분포)을 수행합니다."""
        # PIL의 HSV 변환
        img_pil = Image.fromarray(img_array)
        img_hsv = img_pil.convert("HSV")
        hsv_array = np.array(img_hsv)

        hue = hsv_array[:, :, 0]
        saturation = hsv_array[:, :, 1]
        value = hsv_array[:, :, 2]

        mean_saturation = float(np.mean(saturation))
        mean_value = float(np.mean(value))

        # 채도 상태
        if mean_saturation < 40:
            saturation_status = "낮은 채도 (탁함)"
        elif mean_saturation > 180:
            saturation_status = "과도한 채도"
        elif mean_saturation > 130:
            saturation_status = "높은 채도"
        elif mean_saturation < 70:
            saturation_status = "약간 낮은 채도"
        else:
            saturation_status = "적절한 채도"

        # 지배적 색상 (Hue 분포)
        hue_hist, _ = np.histogram(hue, bins=12, range=(0, 255))
        hue_labels = [
            "빨강", "주황", "노랑", "연두", "초록", "청록",
            "시안", "파랑", "남색", "보라", "자주", "분홍"
        ]
        dominant_idx = int(np.argmax(hue_hist))
        dominant_color = hue_labels[dominant_idx]

        return {
            "saturation_status": saturation_status,
            "mean_saturation": round(mean_saturation, 1),
            "mean_value": round(mean_value, 1),
            "dominant_color": dominant_color,
            "hue_distribution": {
                label: int(count) for label, count in zip(hue_labels, hue_hist)
            },
        }

    def _calculate_quality_score(
        self, exposure, white_balance, noise, sharpness, color
    ) -> dict:
        """종합 품질 점수를 계산합니다."""
        scores = {}

        # 노출 점수 (25점 만점)
        brightness_diff = abs(exposure["mean_brightness"] - 127)
        scores["exposure"] = max(0, 25 - brightness_diff / 5)

        # 화이트밸런스 점수 (20점 만점)
        wb_ratio_diff = abs(white_balance["rg_ratio"] - 1.0) + abs(
            white_balance["bg_ratio"] - 1.0
        )
        scores["white_balance"] = max(0, 20 - wb_ratio_diff * 50)

        # 노이즈 점수 (20점 만점)
        scores["noise"] = max(0, 20 - noise["level"] * 100)

        # 선명도 점수 (20점 만점)
        if sharpness["score"] > 500:
            scores["sharpness"] = 20
        elif sharpness["score"] > 200:
            scores["sharpness"] = 16
        elif sharpness["score"] > 50:
            scores["sharpness"] = 10
        else:
            scores["sharpness"] = 5

        # 색상 점수 (15점 만점)
        sat_diff = abs(color["mean_saturation"] - 100)
        scores["color"] = max(0, 15 - sat_diff / 10)

        total = sum(scores.values())

        return {
            "total": round(total, 1),
            "grade": "A" if total >= 85 else "B" if total >= 70 else "C" if total >= 55 else "D" if total >= 40 else "F",
            "breakdown": {k: round(v, 1) for k, v in scores.items()},
        }

    def _generate_suggestions(
        self, exposure, white_balance, noise, sharpness, color, histogram
    ) -> list:
        """분석 결과를 기반으로 보정 제안을 생성합니다."""
        suggestions = []

        # 노출 보정
        if exposure["suggested_ev_correction"] != 0:
            suggestions.append(
                {
                    "category": "노출 보정",
                    "description": f"현재 {exposure['status']}입니다. 밝기를 조정하세요.",
                    "priority": "high" if abs(exposure["suggested_ev_correction"]) > 0.5 else "medium",
                    "recommended_value": f"밝기 {'+' if exposure['suggested_ev_correction'] > 0 else ''}{int(exposure['suggested_ev_correction'] * 30)}",
                    "param": {
                        "brightness": int(exposure["suggested_ev_correction"] * 30)
                    },
                }
            )

        # 대비 보정
        if exposure["contrast"] == "낮음":
            suggestions.append(
                {
                    "category": "대비 보정",
                    "description": "이미지 대비가 낮아 밋밋해 보입니다. 대비를 높이세요.",
                    "priority": "medium",
                    "recommended_value": "대비 +20~+40",
                    "param": {"contrast": 30},
                }
            )
        elif exposure["contrast"] == "높음":
            suggestions.append(
                {
                    "category": "대비 보정",
                    "description": "대비가 다소 높습니다. 필요 시 약간 낮추세요.",
                    "priority": "low",
                    "recommended_value": "대비 -10~-20",
                    "param": {"contrast": -15},
                }
            )

        # 화이트밸런스
        if white_balance["status"] == "조정 필요":
            suggestions.append(
                {
                    "category": "화이트밸런스",
                    "description": f"{white_balance['color_temp_bias']}. {white_balance['suggestion']}.",
                    "priority": "high",
                    "recommended_value": f"색온도 조정 필요",
                    "param": {
                        "temperature": -20
                        if "따뜻" in white_balance["color_temp_bias"]
                        else 20
                    },
                }
            )

        # 노이즈 제거
        if noise["suggested_denoise_strength"] != "불필요":
            strength_map = {"약": 3, "중": 6, "강": 10}
            suggestions.append(
                {
                    "category": "노이즈 제거",
                    "description": f"{noise['status']}이 감지되었습니다. 디노이징을 적용하세요.",
                    "priority": "medium" if noise["level"] > 0.08 else "low",
                    "recommended_value": f"디노이즈 강도: {noise['suggested_denoise_strength']}",
                    "param": {
                        "denoise": strength_map.get(
                            noise["suggested_denoise_strength"], 0
                        )
                    },
                }
            )

        # 선명도
        if sharpness["score"] < 200:
            suggestions.append(
                {
                    "category": "선명도",
                    "description": f"이미지가 {sharpness['status']}합니다. {sharpness['suggestion']}.",
                    "priority": "medium" if sharpness["score"] < 50 else "low",
                    "recommended_value": "샤프닝 +30~+60",
                    "param": {
                        "sharpness": 50 if sharpness["score"] < 50 else 30
                    },
                }
            )

        # 채도
        if "낮은" in color["saturation_status"]:
            suggestions.append(
                {
                    "category": "채도 보정",
                    "description": "색감이 부족합니다. 채도를 높여 생동감을 추가하세요.",
                    "priority": "medium",
                    "recommended_value": "채도 +15~+30",
                    "param": {"saturation": 25},
                }
            )
        elif "과도" in color["saturation_status"]:
            suggestions.append(
                {
                    "category": "채도 보정",
                    "description": "채도가 과도합니다. 자연스러운 색감을 위해 낮추세요.",
                    "priority": "medium",
                    "recommended_value": "채도 -15~-25",
                    "param": {"saturation": -20},
                }
            )

        # 클리핑 경고
        if exposure["clipped_shadows_pct"] > 5:
            suggestions.append(
                {
                    "category": "섀도우 복구",
                    "description": f"어두운 영역의 {exposure['clipped_shadows_pct']:.1f}%가 클리핑되었습니다. 섀도우를 밝게 하세요.",
                    "priority": "high",
                    "recommended_value": "섀도우 +30~+50",
                    "param": {"shadows": 40},
                }
            )

        if exposure["clipped_highlights_pct"] > 5:
            suggestions.append(
                {
                    "category": "하이라이트 복구",
                    "description": f"밝은 영역의 {exposure['clipped_highlights_pct']:.1f}%가 클리핑되었습니다. 하이라이트를 낮추세요.",
                    "priority": "high",
                    "recommended_value": "하이라이트 -30~-50",
                    "param": {"highlights": -40},
                }
            )

        # 제안이 없으면
        if not suggestions:
            suggestions.append(
                {
                    "category": "종합",
                    "description": "이미지 상태가 양호합니다! 미세 조정만 필요합니다.",
                    "priority": "low",
                    "recommended_value": "미세 조정",
                    "param": {},
                }
            )

        # 우선순위 정렬
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return suggestions

    def _generate_histogram_image(self, img_array: np.ndarray) -> str:
        """히스토그램 이미지를 생성하여 Base64로 반환합니다."""
        try:
            # matplotlib 없이 순수 PIL로 히스토그램 생성
            hist_width = 512
            hist_height = 200
            hist_img = Image.new("RGB", (hist_width, hist_height), (30, 30, 30))

            from PIL import ImageDraw

            draw = ImageDraw.Draw(hist_img)

            colors = [(220, 50, 50), (50, 200, 50), (50, 100, 220)]
            channel_names = ["R", "G", "B"]

            for ch_idx, (color, name) in enumerate(zip(colors, channel_names)):
                channel = img_array[:, :, ch_idx].flatten()
                hist, _ = np.histogram(channel, bins=256, range=(0, 255))
                max_val = max(hist.max(), 1)
                hist_normalized = hist / max_val

                points = []
                for i in range(256):
                    x = int(i * hist_width / 256)
                    y = int(hist_height - hist_normalized[i] * (hist_height - 20))
                    points.append((x, y))

                # 라인 그리기
                for i in range(len(points) - 1):
                    # 반투명 효과를 위해 alpha 조절된 색상 사용
                    draw.line(
                        [points[i], points[i + 1]],
                        fill=(color[0], color[1], color[2]),
                        width=1,
                    )

            # 이미지를 base64로 변환
            buffered = io.BytesIO()
            hist_img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{img_str}"

        except Exception:
            return ""
