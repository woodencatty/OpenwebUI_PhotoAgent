"""
title: PhotoAgent Filter
author: PhotoAgent
description: 사진 보정 에이전트의 대화 흐름을 제어하는 필터입니다. 이미지 업로드 감지 시 사진 분석 컨텍스트를 자동 주입하고, 보정 결과를 포맷팅합니다.
requirements: pillow
version: 1.0.0
"""

import json
import re
from typing import Optional, Dict, List

from pydantic import BaseModel, Field


class Filter:
    """
    PhotoAgent 대화 흐름 제어 필터

    - Inlet: 이미지가 포함된 메시지 감지 시 보정 워크플로우 컨텍스트를 주입
    - Outlet: 보정 결과 메시지를 포맷팅
    """

    class Valves(BaseModel):
        # 필터 설정 (OpenWebUI UI에서 변경 가능)
        auto_analyze: bool = Field(
            default=True,
            description="이미지 업로드 시 자동 분석 제안 활성화",
        )
        analysis_prompt_ko: bool = Field(
            default=True,
            description="한국어 프롬프트 사용",
        )
        max_image_size_mb: float = Field(
            default=50.0,
            description="처리 가능한 최대 이미지 크기 (MB)",
        )
        supported_raw_extensions: str = Field(
            default="cr2,cr3,dng,nef,arw,raf",
            description="지원하는 RAW 파일 확장자 (쉼표 구분)",
        )
        workflow_mode: str = Field(
            default="guided",
            description="워크플로우 모드: 'guided' (가이드 모드) 또는 'auto' (자동 보정)",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        사용자 메시지가 모델로 전달되기 전에 처리합니다.
        이미지가 포함된 메시지를 감지하고, 보정 워크플로우 컨텍스트를 주입합니다.
        """
        if not body.get("messages"):
            return body

        # 마지막 사용자 메시지 확인
        last_message = body["messages"][-1]
        if last_message.get("role") != "user":
            return body

        # 이미지 포함 여부 확인
        has_image = self._detect_image(last_message)
        has_raw_file = self._detect_raw_file(last_message)

        if has_image or has_raw_file:
            # 보정 관련 키워드 감지
            content_text = self._get_text_content(last_message)
            is_photo_request = self._is_photo_editing_request(content_text)

            if is_photo_request or self.valves.auto_analyze:
                # 시스템 메시지에 보정 워크플로우 컨텍스트 주입
                workflow_context = self._generate_workflow_context(
                    has_image=has_image,
                    has_raw=has_raw_file,
                    user_text=content_text,
                )

                # 기존 시스템 메시지 뒤에 컨텍스트 추가
                system_injected = False
                for msg in body["messages"]:
                    if msg.get("role") == "system":
                        msg["content"] += f"\n\n{workflow_context}"
                        system_injected = True
                        break

                if not system_injected:
                    # 시스템 메시지가 없으면 새로 추가
                    body["messages"].insert(
                        0,
                        {
                            "role": "system",
                            "content": workflow_context,
                        },
                    )

        return body

    async def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        모델 응답이 사용자에게 전달되기 전에 처리합니다.
        보정 결과 메시지를 포맷팅하고, 추가 안내를 덧붙입니다.
        """
        if not body.get("messages"):
            return body

        # 마지막 어시스턴트 메시지 확인
        last_message = None
        for msg in reversed(body["messages"]):
            if msg.get("role") == "assistant":
                last_message = msg
                break

        if last_message is None:
            return body

        content = last_message.get("content", "")

        # 보정 완료 메시지 감지 시 추가 안내 삽입
        if "보정 완료" in content or "현상 완료" in content:
            follow_up = self._generate_follow_up_guide()
            last_message["content"] = content + follow_up

        return body

    def _detect_image(self, message: dict) -> bool:
        """메시지에 이미지가 포함되어 있는지 확인합니다."""
        content = message.get("content", "")

        # 문자열 타입인 경우
        if isinstance(content, str):
            # data URL 이미지 확인
            if "data:image" in content:
                return True
            # 이미지 URL 패턴 확인
            image_patterns = [
                r"https?://[^\s]+\.(jpg|jpeg|png|gif|webp|bmp|tiff)",
                r"/api/v1/files/[^\s]+",
            ]
            for pattern in image_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True

        # 멀티파트 콘텐츠 (리스트 타입) 인 경우
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "image_url":
                        return True
                    if part.get("type") == "image":
                        return True

        # 파일 첨부 확인
        if message.get("images"):
            return True

        return False

    def _detect_raw_file(self, message: dict) -> bool:
        """메시지에 RAW 파일이 포함되어 있는지 확인합니다."""
        content = self._get_text_content(message)
        supported = self.valves.supported_raw_extensions.split(",")

        for ext in supported:
            if f".{ext.strip()}" in content.lower():
                return True

        # 파일 첨부 확인
        files = message.get("files", [])
        if isinstance(files, list):
            for f in files:
                if isinstance(f, dict):
                    filename = f.get("name", "").lower()
                    for ext in supported:
                        if filename.endswith(f".{ext.strip()}"):
                            return True

        return False

    def _get_text_content(self, message: dict) -> str:
        """메시지에서 텍스트 콘텐츠를 추출합니다."""
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    texts.append(part.get("text", ""))
                elif isinstance(part, str):
                    texts.append(part)
            return " ".join(texts)
        return ""

    def _is_photo_editing_request(self, text: str) -> bool:
        """텍스트가 사진 보정 요청인지 판단합니다."""
        keywords_ko = [
            "보정", "편집", "수정", "밝게", "어둡게", "선명", "채도",
            "필터", "색감", "노출", "화이트밸런스", "대비", "톤",
            "리터칭", "리터치", "현상", "프리셋", "보정해", "고쳐",
            "살려", "노이즈", "선명하게", "따뜻하게", "차갑게",
            "분석", "품질", "개선",
        ]
        keywords_en = [
            "edit", "retouch", "enhance", "fix", "correct",
            "brightness", "contrast", "saturation", "sharpen",
            "filter", "preset", "raw", "exposure", "process",
        ]

        text_lower = text.lower()
        for keyword in keywords_ko + keywords_en:
            if keyword in text_lower:
                return True

        return False

    def _generate_workflow_context(
        self, has_image: bool, has_raw: bool, user_text: str
    ) -> str:
        """보정 워크플로우 컨텍스트를 생성합니다."""
        context = "\n--- [PhotoAgent 워크플로우 컨텍스트] ---\n"

        if has_raw:
            context += """
[RAW 파일 감지됨]
사용자가 RAW 파일을 업로드했습니다. 다음 워크플로우를 따르세요:

1단계 - RAW 정보 확인: `get_raw_info` 도구로 RAW 파일의 메타데이터를 먼저 확인하세요.
2단계 - RAW 현상: `process_raw` 도구로 RAW 파일을 현상하세요. 카메라 화이트밸런스를 기본 사용하고, 사용자 요청에 따라 파라미터를 조정하세요.
3단계 - 분석: 현상된 이미지를 `analyze_photo` 도구로 분석하세요.
4단계 - 보정 제안: 분석 결과를 바탕으로 보정 방향을 제안하세요.
5단계 - 보정 실행: 사용자 확인 후 `edit_photo` 도구로 보정을 실행하세요.
"""
        elif has_image:
            if self.valves.workflow_mode == "guided":
                context += """
[이미지 감지됨 - 가이드 모드]
사용자가 이미지를 업로드했습니다. 다음 워크플로우를 따르세요:

1단계 - 분석: `analyze_photo` 도구를 호출하여 이미지를 기술적으로 분석하세요.
2단계 - 결과 설명: 분석 결과를 사용자에게 이해하기 쉽게 설명하세요:
  - 현재 이미지의 장점과 개선할 점
  - 각 보정 항목의 의미와 효과
  - 추천 보정 방향과 그 이유
3단계 - 보정 제안: 구체적인 보정 파라미터를 제안하고 사용자에게 확인을 요청하세요.
4단계 - 보정 실행: 사용자가 승인하면 `edit_photo` 도구로 보정을 실행하세요.
5단계 - 후속 조치: 보정 결과를 보여주고, 추가 조정이 필요한지 물어보세요.

중요: 항상 사용자에게 보정 방향을 먼저 설명하고, 승인을 받은 후에 보정을 실행하세요.
프리셋을 제안할 때는 `apply_preset` 도구의 프리셋 목록을 참고하세요.
"""
            else:
                context += """
[이미지 감지됨 - 자동 모드]
사용자가 이미지를 업로드했습니다. 자동으로 분석하고 최적의 보정을 적용하세요:

1. `analyze_photo`로 분석
2. 분석 결과의 suggestions를 기반으로 자동 보정 파라미터 결정
3. `edit_photo`로 보정 실행
4. 결과를 사용자에게 보여주기
"""

        context += "\n--- [/PhotoAgent 워크플로우 컨텍스트] ---\n"
        return context

    def _generate_follow_up_guide(self) -> str:
        """보정 완료 후 후속 안내를 생성합니다."""
        return """

---
### 💡 추가 옵션
- 🔄 **다시 보정하기**: 다른 파라미터로 재보정을 요청할 수 있습니다
- 🎨 **프리셋 적용**: `portrait`, `landscape`, `food`, `street`, `film_vintage`, `bright_airy`, `moody_dark`, `golden_hour`, `clean_natural` 프리셋을 사용할 수 있습니다
- 📊 **재분석**: 보정된 이미지를 다시 분석할 수 있습니다
- ✏️ **미세 조정**: 특정 항목만 추가로 조정할 수 있습니다 (예: "채도만 좀 더 높여줘")
"""
