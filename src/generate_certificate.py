import os
from datetime import datetime
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    # Try common fonts; fall back to default
    candidates = [
        ("arial.ttf", None),
        ("DejaVuSans.ttf", None),
    ]
    for name, _ in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()

def generate_certificate(
    name: str,
    award_title: str = "Certificate of Achievement",
    output_path: Optional[str] = None,
) -> str:
    """
    Creates a certificate PNG and returns the saved file path.
    Default output: certificates/<name>_certificate.png
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUT_DIR = os.path.join(BASE_DIR, "certificates")
    os.makedirs(OUT_DIR, exist_ok=True)

    safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    if not safe_name:
        safe_name = "Unknown"

    if output_path is None:
        output_path = os.path.join(OUT_DIR, f"{safe_name}_certificate.png")

    # Canvas
    W, H = 1400, 1000
    img = Image.new("RGB", (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)

    # Border
    margin = 40
    draw.rectangle([margin, margin, W - margin, H - margin], outline=(110, 231, 255), width=6)

    # Headline
    title_font = _load_font(64)
    subtitle_font = _load_font(34)
    name_font = _load_font(60)
    small_font = _load_font(26)

    def center(text, y, font, fill=(232, 236, 255)):
        w = draw.textlength(text, font=font)
        draw.text(((W - w) / 2, y), text, font=font, fill=fill)

    center(award_title.upper(), 140, title_font, fill=(110, 231, 255))
    center("This certificate is proudly presented to", 270, subtitle_font, fill=(169, 178, 212))
    center(name, 360, name_font, fill=(232, 236, 255))
    center("For outstanding performance and dedication.", 460, subtitle_font, fill=(169, 178, 212))

    date_str = datetime.now().strftime("%d %b %Y")
    center(f"Date: {date_str}", 720, small_font, fill=(169, 178, 212))
    center("Face Reward System", 780, small_font, fill=(169, 178, 212))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    return output_path

if __name__ == "__main__":
    path = generate_certificate("Demo User", "Best Performer")
    print("Saved:", path)
