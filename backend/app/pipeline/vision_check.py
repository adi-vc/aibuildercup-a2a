"""
Vision Check — OCR Detection for Baked Text

This module uses Vision AI to detect any baked-in text in generated plates.

Why this matters: A plate with hardcoded English text can't be localized.
The vision check ensures plates are text-free, so all copy comes from
text_slots that can be swapped at play-time.

In production, this would:
- Run OCR on every generated plate
- Reject plates with detected text (except logos/brand marks)
- Retry generation with "no text" prompt reinforcement

For the hackathon demo, this is a SCAFFOLD showing the safety check.
Hand-curated plates are manually verified to have no baked text.
"""

from typing import List, Dict, Any
from pathlib import Path


class BakedTextDetection:
    """Result of OCR scan on a plate."""
    text_found: bool
    detected_strings: List[str]
    confidence: float
    
    def __init__(self, text_found: bool, detected_strings: List[str], confidence: float = 0.0):
        self.text_found = text_found
        self.detected_strings = detected_strings
        self.confidence = confidence


def check_for_baked_text(image_path: Path) -> BakedTextDetection:
    """
    Scan a generated plate for any baked-in text via OCR.
    
    Args:
        image_path: Path to the plate image
    
    Returns:
        BakedTextDetection with:
        - text_found: True if any text detected
        - detected_strings: List of OCR'd text fragments
        - confidence: OCR confidence score
    
    Production implementation:
    ```python
    from google.cloud import vision
    
    client = vision.ImageAnnotatorClient()
    with open(image_path, 'rb') as f:
        image = vision.Image(content=f.read())
    
    response = client.text_detection(image=image)
    texts = response.text_annotations
    
    if texts:
        # texts[0] is the full detected text
        # texts[1:] are individual word bounding boxes
        detected = [text.description for text in texts]
        return BakedTextDetection(
            text_found=True,
            detected_strings=detected,
            confidence=texts[0].confidence if texts else 0.0
        )
    
    return BakedTextDetection(text_found=False, detected_strings=[], confidence=1.0)
    ```
    
    Demo: assumes manual verification, returns pass.
    """
    
    # In demo, we manually verify curated plates have no text
    # Return stub showing the interface
    return BakedTextDetection(
        text_found=False,
        detected_strings=[],
        confidence=1.0
    )


def validate_plate(image_path: Path, allow_logos: bool = True) -> Dict[str, Any]:
    """
    Full plate validation pipeline.
    
    Checks:
    1. No baked text (OCR)
    2. Appropriate dimensions (1920×1080 or 16:9)
    3. File size reasonable (< 5MB for WebP)
    
    Args:
        image_path: Path to plate
        allow_logos: If True, ignore small text regions (brand logos)
    
    Returns:
        {
            "valid": bool,
            "checks": {
                "no_baked_text": bool,
                "dimensions_ok": bool,
                "file_size_ok": bool
            },
            "warnings": List[str],
            "errors": List[str]
        }
    """
    
    result = {
        "valid": True,
        "checks": {
            "no_baked_text": True,
            "dimensions_ok": True,
            "file_size_ok": True
        },
        "warnings": [],
        "errors": []
    }
    
    # Check 1: OCR
    ocr_result = check_for_baked_text(image_path)
    if ocr_result.text_found:
        # Filter out allowed logos if needed
        disallowed_text = [t for t in ocr_result.detected_strings if len(t) > 3]
        if disallowed_text:
            result["valid"] = False
            result["checks"]["no_baked_text"] = False
            result["errors"].append(f"Baked text detected: {disallowed_text}")
    
    # Check 2: Dimensions (basic check, would use PIL/Pillow in production)
    if image_path.exists():
        # In production: check actual dimensions
        # from PIL import Image
        # img = Image.open(image_path)
        # if img.width / img.height != 16/9:
        #     result["warnings"].append("Non-16:9 aspect ratio")
        pass
    
    # Check 3: File size
    if image_path.exists():
        size_mb = image_path.stat().st_size / (1024 * 1024)
        if size_mb > 5:
            result["warnings"].append(f"Large file size: {size_mb:.2f}MB")
            result["checks"]["file_size_ok"] = False
    
    return result


# Example usage (not called in current demo flow)
if __name__ == "__main__":
    from pathlib import Path
    
    # Demo: validate a placeholder
    plate_path = Path("../../../frontend/public/assets/placeholder_flood_street.png")
    
    if plate_path.exists():
        result = validate_plate(plate_path)
        print(f"Validation: {'✓ PASS' if result['valid'] else '✗ FAIL'}")
        print(f"Checks: {result['checks']}")
        if result['errors']:
            print(f"Errors: {result['errors']}")
        if result['warnings']:
            print(f"Warnings: {result['warnings']}")
