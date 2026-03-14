"""CLI entry point for Vision Agent.

Usage:
    python -m vision_agent <image_path> [image_path ...] [--provider mock|sealion|gemini] [--json]

Examples:
    python -m vision_agent meal.jpg
    python -m vision_agent front.jpg back.jpg              # multi-image
    python -m vision_agent prescription.png --provider sealion
    python -m vision_agent report.jpg --json
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from src.vision_agent.config import VLMProvider, get_settings
from src.vision_agent.graph import build_graph
from src.vision_agent.llm.base import BaseVLM, VLMError
from src.vision_agent.llm.gemini import GeminiVLM
from src.vision_agent.llm.mock import MockVLM
from src.vision_agent.llm.sealion import SeaLionVLM
from src.vision_agent.logging_config import configure_logging


def _build_vlm(provider: VLMProvider) -> BaseVLM:
    """Build the vision VLM based on provider setting."""
    if provider == VLMProvider.GEMINI:
        return GeminiVLM()
    if provider == VLMProvider.SEALION:
        return SeaLionVLM()
    return MockVLM()


def _build_text_llm() -> BaseVLM | None:
    """Build SeaLION text LLM if API key is available."""
    settings = get_settings()
    if settings.sealion_api_key:
        try:
            return SeaLionVLM()
        except VLMError:
            return None
    return None


def _print_result(result: dict, as_json: bool) -> None:
    output = result.get("structured_output", {})
    advice = result.get("advice", "")
    scene = output.get("scene_type", "UNKNOWN")

    if as_json:
        combined = {"recognition": output}
        if advice:
            try:
                combined["advice"] = json.loads(advice)
            except (json.JSONDecodeError, TypeError):
                combined["advice"] = advice
        print(json.dumps(combined, indent=2, ensure_ascii=False))
        return

    # ── Human-readable output ──────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"  Scene: {scene}  |  Confidence: {output.get('confidence', 0):.0%}")
    print(f"{'='*50}")

    if scene == "FOOD":
        print(f"  Food    : {output.get('food_name', '?')}")
        print(f"  GI Level: {output.get('gi_level', '?')}")
        print(f"  Calories: {output.get('total_calories', '?')} kcal")

    elif scene == "MEDICATION":
        print(f"  Drug    : {output.get('drug_name', '?')}")
        print(f"  Dosage  : {output.get('dosage', '?')}")
        print(f"  Freq    : {output.get('frequency', '?')}")
        if output.get("route"):
            print(f"  Route   : {output['route']}")
        if output.get("warnings"):
            print("  Warnings:")
            for w in output["warnings"]:
                print(f"    ⚠ {w}")

    elif scene == "REPORT":
        print(f"  Type: {output.get('report_type', '?')}")
        if output.get("report_date"):
            print(f"  Date: {output['report_date']}")
        print("\n  Indicators:")
        for ind in output.get("indicators", []):
            flag = "⚠ ABNORMAL" if ind.get("is_abnormal") else "  normal  "
            ref = f"  (ref: {ind['reference_range']})" if ind.get("reference_range") else ""
            print(f"    [{flag}] {ind['name']}: {ind['value']} {ind.get('unit', '')}{ref}")

    elif scene == "UNKNOWN":
        print(f"  Rejected: {output.get('reason', 'Unknown reason')}")

    elif scene == "ERROR":
        print(f"  Error: {output.get('error', 'Unknown error')}")

    # Display health advice if available
    if advice and scene not in ("UNKNOWN", "ERROR"):
        print(f"{'─'*50}")
        print("  Health Advice (SeaLION):")
        try:
            advice_data = json.loads(advice)
            if "advice_summary" in advice_data:
                print(f"  {advice_data['advice_summary']}")
            if "suggestions" in advice_data:
                for s in advice_data["suggestions"]:
                    print(f"    - {s}")
            if "encouragement" in advice_data:
                print(f"\n  {advice_data['encouragement']}")
            if "medication_purpose" in advice_data:
                print(f"  Purpose: {advice_data['medication_purpose']}")
            if "key_reminders" in advice_data:
                for r in advice_data["key_reminders"]:
                    print(f"    - {r}")
            if "overall_assessment" in advice_data:
                print(f"  {advice_data['overall_assessment']}")
            if "lifestyle_tips" in advice_data:
                for t in advice_data["lifestyle_tips"]:
                    print(f"    - {t}")
        except (json.JSONDecodeError, TypeError):
            print(f"  {advice}")

    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vision Agent - analyze medical images (food, medication, reports)"
    )
    parser.add_argument(
        "image_paths",
        nargs="+",
        help="Path(s) to image file(s) to analyze",
    )
    parser.add_argument(
        "--provider",
        choices=["mock", "sealion", "gemini"],
        default=None,
        help="VLM provider to use (default: from .env or 'mock')",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output raw JSON instead of human-readable format",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)

    # CLI --provider flag overrides env setting
    provider = VLMProvider(args.provider) if args.provider else settings.vlm_provider

    try:
        vlm = _build_vlm(provider)
    except VLMError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Build text LLM (SeaLION) for health advice — optional
    text_llm = _build_text_llm() if provider != VLMProvider.MOCK else None

    graph = build_graph(
        vlm=vlm,
        text_llm=text_llm,
        max_retries=settings.vlm_max_retries,
        retry_delay_s=settings.vlm_retry_delay_s,
    )

    resolved_paths = [str(Path(p).resolve()) for p in args.image_paths]

    initial_state = {
        "image_paths": resolved_paths,
        "images_base64": [],
        "scene_type": "",
        "confidence": 0.0,
        "raw_response": "",
        "structured_output": {},
        "advice": "",
        "error": None,
    }

    if not args.as_json:
        advisor_status = text_llm.model_name if text_llm else "disabled"
        img_label = ", ".join(args.image_paths)
        print(f"Analyzing: {img_label}  (vision: {provider.value}, advisor: {advisor_status})")

    result = graph.invoke(initial_state)
    _print_result(result, args.as_json)

    # Exit code 1 if error
    if result.get("structured_output", {}).get("scene_type") == "ERROR":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
