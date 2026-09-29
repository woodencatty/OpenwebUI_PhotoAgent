"""
OpenWebUI PhotoAgent 로컬 기능 검증 및 단위 테스트 스크립트
Tool(분석기, 보정기)과 Filter(워크플로우 제어)가 로컬 환경에서 정상 작동하는지 종합 검증합니다.
"""

import asyncio
import base64
import io
import os
import sys

# Windows 콘솔 인코딩 대응 (UTF-8)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
from PIL import Image, ImageDraw


def create_mock_test_image() -> str:
    """테스트용 합성 이미지 생성 (어둡고 푸르스름한 톤) -> Base64 data URL 반환"""
    width, height = 640, 480
    # 약간 어둡고 푸른 톤을 띤 그라데이션 이미지 생성
    img_array = np.zeros((height, width, 3), dtype=np.uint8)

    # 배경 그라데이션 (어두운 푸른 계열)
    for y in range(height):
        for x in range(width):
            r = int(50 + 40 * (x / width))
            g = int(60 + 50 * (y / height))
            b = int(120 + 60 * (x / width))
            img_array[y, x] = [r, g, b]

    img = Image.fromarray(img_array)
    draw = ImageDraw.Draw(img)

    # 가운데 모의 피사체 (밝은 원 및 사각형)
    draw.ellipse([220, 140, 420, 340], fill=(160, 140, 120), outline=(200, 180, 150))
    draw.rectangle([280, 200, 360, 280], fill=(90, 80, 70))
    draw.text((250, 400), "PhotoAgent Test Sample", fill=(220, 220, 240))

    # Base64 Data URL로 변환
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"


async def run_tests():
    print("==================================================")
    print("🚀 OpenWebUI PhotoAgent 종합 기능 검증 시작")
    print("==================================================")

    # 1. 샘플 이미지 생성
    print("\n[1단계] 테스트용 샘플 이미지 생성...")
    sample_data_url = create_mock_test_image()
    print(f"✅ 샘플 이미지 생성 완료 (Data URL 길이: {len(sample_data_url)} bytes)")

    # 2. Photo Analyzer 검증
    print("\n[2단계] Photo Analyzer (사진 분석기) 테스트...")
    try:
        from tools.photo_analyzer import Tools as AnalyzerTools

        analyzer = AnalyzerTools()
        analysis_result = await analyzer.analyze_photo(image_url=sample_data_url)
        print("✅ 분석 완료! 출력 결과 요약:")
        # 결과 첫 15줄 출력
        for line in analysis_result.split("\n")[:15]:
            print(f"   {line}")
        print("   ...")
        assert "📊 사진 분석 리포트" in analysis_result, "분석 리포트 헤더 누락"
        assert "종합 품질 점수" in analysis_result, "품질 점수 누락"
        assert "보정 제안" in analysis_result, "보정 제안 누락"
    except Exception as e:
        print(f"❌ Photo Analyzer 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 3. Photo Editor 개별 파라미터 보정 검증
    print("\n[3단계] Photo Editor (파라미터 보정) 테스트...")
    try:
        from tools.photo_editor import Tools as EditorTools

        editor = EditorTools()
        edit_result = await editor.edit_photo(
            image_url=sample_data_url,
            brightness=20,
            contrast=15,
            temperature=10,
            sharpness=25,
            vignette=10,
        )
        print("✅ 파라미터 보정 완료! 출력 결과 요약:")
        for line in edit_result.split("\n")[:12]:
            print(f"   {line}")
        print("   ...")
        assert "🎨 사진 보정 완료!" in edit_result, "보정 완료 헤더 누락"
        assert "보정 전/후 비교" in edit_result, "비교 이미지 누락"
        assert "보정된 사진 다운로드" in edit_result, "다운로드 링크 누락"
    except Exception as e:
        print(f"❌ Photo Editor 파라미터 보정 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. Photo Editor 프리셋 보정 검증
    print("\n[4단계] Photo Editor (프리셋 보정) 테스트...")
    try:
        preset_result = await editor.apply_preset(
            image_url=sample_data_url,
            preset_name="clean_natural",
            intensity=80,
        )
        print("✅ 'clean_natural' 프리셋 적용 완료!")
        assert "🎨 사진 보정 완료!" in preset_result, "프리셋 보정 완료 헤더 누락"
    except Exception as e:
        print(f"❌ Photo Editor 프리셋 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. Filter (Inlet/Outlet 워크플로우 제어) 검증
    print("\n[5단계] PhotoAgent Filter (대화 흐름 제어) 테스트...")
    try:
        from filters.photo_agent_filter import Filter

        photo_filter = Filter()

        # 5-1. Inlet 테스트: 이미지가 첨부된 사용자 요청
        mock_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "이 사진 좀 화사하게 보정해줄래?"},
                        {"type": "image_url", "image_url": {"url": sample_data_url}},
                    ],
                }
            ]
        }

        inlet_processed = await photo_filter.inlet(mock_body)
        first_msg = inlet_processed["messages"][0]
        assert first_msg["role"] == "system", "시스템 컨텍스트 주입 실패"
        assert "PhotoAgent 워크플로우 컨텍스트" in first_msg["content"], "워크플로우 지침 주입 실패"
        print("✅ Filter Inlet: 이미지 감지 및 시스템 가이드 자동 주입 정상 동작!")

        # 5-2. Outlet 테스트: 모델 응답 후 후속 가이드 첨부
        mock_response_body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "사진 보정 완료되었습니다. 전/후 비교 이미지를 확인해보세요!",
                }
            ]
        }
        outlet_processed = await photo_filter.outlet(mock_response_body)
        assistant_content = outlet_processed["messages"][0]["content"]
        assert "추가 옵션" in assistant_content, "후속 가이드 안내 주입 실패"
        print("✅ Filter Outlet: 보정 완료 감지 및 후속 선택 옵션 자동 안내 정상 동작!")

    except Exception as e:
        print(f"❌ Filter 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n==================================================")
    print("🎉 모든 테스트 통과! PhotoAgent가 정상적으로 준비되었습니다.")
    print("==================================================")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
