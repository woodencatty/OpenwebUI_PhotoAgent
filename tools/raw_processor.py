"""
title: RAW Processor
author: PhotoAgent
description: Canon CR2, Samsung DNG 등 RAW 파일을 처리하여 JPEG/PNG로 변환하고, 기본적인 RAW 현상 파라미터를 적용하는 도구입니다.
requirements: rawpy, numpy, pillow, imageio
version: 1.0.0
"""

import base64
import io
import json
import os
import time
import uuid
from typing import Optional

import numpy as np
from PIL import Image


class Tools:
    """RAW 파일 처리 도구 - CR2, DNG 등 RAW 파일을 현상하고 변환합니다."""

    DEFAULT_OPENWEBUI_SAVE_DIR = "/app/backend/data/uploads/raw_processor"
    DEFAULT_OPENWEBUI_TEMP_DIR = "/app/backend/data/uploads/raw_temp"
    FALLBACK_SAVE_DIR = os.path.join(os.getcwd(), "uploads", "raw_processor")
    FALLBACK_TEMP_DIR = os.path.join(os.getcwd(), "uploads", "raw_temp")

    def __init__(self):
        try:
            if os.path.exists("/app/backend/data/uploads") or os.access("/app", os.W_OK):
                self.SAVE_DIR = self.DEFAULT_OPENWEBUI_SAVE_DIR
                self.TEMP_DIR = self.DEFAULT_OPENWEBUI_TEMP_DIR
            else:
                self.SAVE_DIR = self.FALLBACK_SAVE_DIR
                self.TEMP_DIR = self.FALLBACK_TEMP_DIR
            os.makedirs(self.SAVE_DIR, exist_ok=True)
            os.makedirs(self.TEMP_DIR, exist_ok=True)
        except Exception:
            self.SAVE_DIR = self.FALLBACK_SAVE_DIR
            self.TEMP_DIR = self.FALLBACK_TEMP_DIR
            os.makedirs(self.SAVE_DIR, exist_ok=True)
            os.makedirs(self.TEMP_DIR, exist_ok=True)

    async def process_raw(
        self,
        file_path: str,
        use_camera_wb: bool = True,
        auto_brightness: bool = True,
        half_size: bool = False,
        output_bps: int = 8,
        gamma: str = "srgb",
        highlight_mode: int = 0,
        chromatic_aberration: bool = False,
        output_format: str = "jpeg",
        quality: int = 95,
        __event_emitter__=None,
    ) -> str:
        """
        RAW 파일(CR2, DNG, NEF, ARW 등)을 처리하여 JPEG 또는 PNG로 변환합니다.

        :param file_path: RAW 파일 경로 (OpenWebUI 업로드 경로)
        :param use_camera_wb: 카메라에 저장된 화이트밸런스 사용 여부 (기본: True)
        :param auto_brightness: 자동 밝기 조정 (기본: True)
        :param half_size: 절반 크기로 처리 (빠른 미리보기용, 기본: False)
        :param output_bps: 출력 비트 심도 (8 또는 16, 기본: 8)
        :param gamma: 감마 설정 ('srgb', 'linear', 'bt709')
        :param highlight_mode: 하이라이트 복구 모드 (0=클립, 1=무시, 2=블렌드, 3=재구성)
        :param chromatic_aberration: 색수차 보정 활성화 (기본: False)
        :param output_format: 출력 형식 ('jpeg' 또는 'png')
        :param quality: JPEG 품질 (1~100, 기본: 95)
        :return: 현상된 이미지 및 RAW 메타데이터
        """
        try:
            import rawpy
        except ImportError:
            return "❌ `rawpy` 패키지가 설치되어 있지 않습니다. OpenWebUI Docker 컨테이너에서 `pip install rawpy`를 실행해주세요."

        try:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "📷 RAW 파일을 읽는 중...",
                            "done": False,
                        },
                    }
                )

            # 파일 경로 확인 및 탐색
            resolved_path = self._resolve_file_path(file_path)
            if not resolved_path:
                return f"❌ 파일을 찾을 수 없습니다: {file_path}\n컨테이너 업로드 디렉토리 또는 유효한 파일 경로를 확인해주세요."
            file_path = resolved_path

            # 파일 확장자 확인
            ext = os.path.splitext(file_path)[1].lower()
            supported_formats = [
                ".cr2", ".cr3",  # Canon
                ".dng",         # Adobe DNG (Samsung Expert RAW 등)
                ".nef",         # Nikon
                ".arw",         # Sony
                ".raf",         # Fujifilm
                ".orf",         # Olympus
                ".rw2",         # Panasonic
                ".pef",         # Pentax
            ]

            if ext not in supported_formats:
                return f"❌ 지원하지 않는 RAW 형식입니다: {ext}\n지원 형식: {', '.join(supported_formats)}"

            # RAW 파일 로드
            with rawpy.imread(file_path) as raw:
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": "🔬 RAW 데이터 현상 중...",
                                "done": False,
                            },
                        }
                    )

                # RAW 메타데이터 추출
                raw_metadata = self._extract_raw_metadata(raw, file_path)

                # 감마 설정
                gamma_map = {
                    "srgb": (2.222, 4.5),
                    "linear": (1, 1),
                    "bt709": (2.222, 4.5),
                }
                gamma_value = gamma_map.get(gamma, (2.222, 4.5))

                # RAW 현상 (포스트프로세싱)
                postprocess_params = {
                    "use_camera_wb": use_camera_wb,
                    "no_auto_bright": not auto_brightness,
                    "half_size": half_size,
                    "output_bps": output_bps,
                    "gamma": gamma_value,
                    "highlight_mode": rawpy.HighlightMode(highlight_mode),
                }

                # 색수차 보정 (지원 여부 확인)
                if chromatic_aberration:
                    postprocess_params["chromatic_aberration"] = (1, 1)

                rgb = raw.postprocess(**postprocess_params)

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "💾 이미지 변환 및 저장 중...",
                            "done": False,
                        },
                    }
                )

            # numpy 배열 → PIL Image
            if output_bps == 16:
                # 16비트를 8비트로 변환 (표시용)
                rgb_8bit = (rgb / 256).astype(np.uint8)
                img = Image.fromarray(rgb_8bit)
            else:
                img = Image.fromarray(rgb)

            # 파일 저장
            file_id = str(uuid.uuid4())[:8]
            timestamp = int(time.time())
            base_name = os.path.splitext(os.path.basename(file_path))[0]

            if output_format.lower() == "png":
                filename = f"{base_name}_{timestamp}_{file_id}.png"
                filepath = os.path.join(self.SAVE_DIR, filename)
                img.save(filepath, "PNG")
            else:
                filename = f"{base_name}_{timestamp}_{file_id}.jpg"
                filepath = os.path.join(self.SAVE_DIR, filename)
                img.save(filepath, "JPEG", quality=quality)

            # Base64 인코딩 (채팅에 표시용)
            buffered = io.BytesIO()
            # 표시용은 크기 제한
            display_img = img.copy()
            max_display = 1200
            if display_img.width > max_display:
                ratio = max_display / display_img.width
                display_img = display_img.resize(
                    (max_display, int(display_img.height * ratio)), Image.LANCZOS
                )

            display_img.save(buffered, format="JPEG", quality=85)
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "✅ RAW 파일 현상 완료!",
                            "done": True,
                        },
                    }
                )

            # 결과 반환
            result = f"## 📷 RAW 파일 현상 완료\n\n"
            result += f"### 📋 RAW 파일 정보\n"
            for key, value in raw_metadata.items():
                result += f"- **{key}**: {value}\n"
            result += "\n"

            result += f"### 🔧 현상 설정\n"
            result += f"- **화이트밸런스**: {'카메라 WB' if use_camera_wb else '자동'}\n"
            result += f"- **자동 밝기**: {'활성' if auto_brightness else '비활성'}\n"
            result += f"- **감마**: {gamma}\n"
            result += f"- **하이라이트 모드**: {['클립', '무시', '블렌드', '재구성'][highlight_mode]}\n"
            result += f"- **출력 형식**: {output_format.upper()} (품질: {quality})\n\n"

            result += f"### 🖼️ 현상 결과\n"
            result += f"![현상된 이미지](data:image/jpeg;base64,{img_b64})\n\n"

            result += f"**이미지 크기**: {img.width}×{img.height}\n"
            result += f"**저장 경로**: `{filepath}`\n"
            result += f"[📥 **현상된 사진 다운로드 (클릭)**](data:image/jpeg;base64,{img_b64})\n\n"

            result += (
                f"> 💡 이 이미지에 추가 보정을 원하시면 "
                f"**Photo Editor** 도구를 사용할 수 있습니다.\n"
                f"> 저장 경로를 이미지 URL로 전달하면 됩니다."
            )

            return result

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"❌ RAW 처리 실패: {str(e)}",
                            "done": True,
                        },
                    }
                )
            return f"❌ RAW 파일 처리 중 오류가 발생했습니다: {str(e)}"

    async def get_raw_info(
        self,
        file_path: str,
        __event_emitter__=None,
    ) -> str:
        """
        RAW 파일의 상세 메타데이터를 추출합니다 (현상 없이 정보만 확인).

        :param file_path: RAW 파일 경로
        :return: RAW 파일 메타데이터 (카메라, 센서, 색공간 정보 등)
        """
        try:
            import rawpy
        except ImportError:
            return "❌ `rawpy` 패키지가 설치되어 있지 않습니다."

        try:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "📋 RAW 파일 정보를 읽는 중...",
                            "done": False,
                        },
                    }
                )

            resolved_path = self._resolve_file_path(file_path)
            if not resolved_path:
                return f"❌ 파일을 찾을 수 없습니다: {file_path}\n컨테이너 업로드 디렉토리 또는 유효한 파일 경로를 확인해주세요."
            file_path = resolved_path

            with rawpy.imread(file_path) as raw:
                metadata = self._extract_raw_metadata(raw, file_path)

                # 추가 상세 정보
                try:
                    metadata["Bayer 패턴"] = raw.raw_pattern.tolist() if raw.raw_pattern is not None else "N/A"
                    metadata["색온도 (카메라)"] = str(raw.camera_whitebalance)
                    metadata["색온도 (일광)"] = str(raw.daylight_whitebalance)
                    metadata["블랙 레벨"] = str(raw.black_level_per_channel)
                    metadata["화이트 레벨"] = str(raw.white_level)
                    metadata["톤커브"] = "있음" if raw.tone_curve is not None else "없음"
                except Exception:
                    pass

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "✅ RAW 정보 추출 완료!",
                            "done": True,
                        },
                    }
                )

            result = f"## 📋 RAW 파일 상세 정보\n\n"
            result += f"**파일**: `{os.path.basename(file_path)}`\n\n"
            for key, value in metadata.items():
                result += f"- **{key}**: {value}\n"

            return result

        except Exception as e:
            return f"❌ RAW 파일 정보 추출 실패: {str(e)}"

    def _resolve_file_path(self, file_path: str) -> Optional[str]:
        """
        다양한 환경(컨테이너 업로드, 로컬 경로 등)에서 RAW 파일의 실제 경로를 탐색합니다.
        """
        if not file_path or not isinstance(file_path, str):
            return None

        clean_path = file_path.strip().strip("\"'")

        # 1. 전달된 경로가 직접 존재하는 경우
        if os.path.exists(clean_path):
            return clean_path

        # 2. OpenWebUI 업로드 및 로컬 후보 디렉토리 탐색
        candidates = [
            clean_path,
            os.path.join(self.SAVE_DIR, os.path.basename(clean_path)),
            os.path.join(self.TEMP_DIR, os.path.basename(clean_path)),
            os.path.join("/app/backend/data/uploads", os.path.basename(clean_path)),
            os.path.join("/app/backend/data/uploads", clean_path.lstrip("/")),
            os.path.join("./uploads", os.path.basename(clean_path)),
        ]

        for candidate in candidates:
            if os.path.exists(candidate) and os.path.isfile(candidate):
                return candidate

        return None

    def _extract_raw_metadata(self, raw, file_path: str) -> dict:
        """RAW 객체에서 메타데이터를 추출합니다."""
        metadata = {}

        try:
            file_size = os.path.getsize(file_path)
            metadata["파일 크기"] = f"{file_size / 1024 / 1024:.1f}MB"
        except Exception:
            pass

        try:
            # 기본 정보
            metadata["RAW 크기"] = f"{raw.sizes.raw_width}×{raw.sizes.raw_height}"
            metadata["출력 크기"] = f"{raw.sizes.width}×{raw.sizes.height}"
            metadata["색 채널 수"] = str(raw.num_colors)
            metadata["컬러 설명"] = raw.color_desc.decode("utf-8") if isinstance(raw.color_desc, bytes) else str(raw.color_desc)
        except Exception as e:
            metadata["기본 정보 오류"] = str(e)

        try:
            # 카메라 정보 (rawpy의 camera_make 등은 버전에 따라 다름)
            metadata["확장자"] = os.path.splitext(file_path)[1].upper()

            # 파일 확장자 기반 카메라 추정
            ext = os.path.splitext(file_path)[1].lower()
            camera_map = {
                ".cr2": "Canon (CR2)",
                ".cr3": "Canon (CR3)",
                ".dng": "DNG (범용 RAW)",
                ".nef": "Nikon (NEF)",
                ".arw": "Sony (ARW)",
                ".raf": "Fujifilm (RAF)",
                ".orf": "Olympus (ORF)",
                ".rw2": "Panasonic (RW2)",
                ".pef": "Pentax (PEF)",
            }
            metadata["RAW 형식"] = camera_map.get(ext, f"알 수 없음 ({ext})")

        except Exception:
            pass

        return metadata
