import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

def generate_certificate(name: str) -> str:
    """
    Creates a certificate PNG and returns the saved file path.
    Output: certificates/<name>_certificate.png
    """
    # Base folders
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUT_DIR = os.path.join(BASE_DIR, "certificates")
    os.makedirs(OUT_DIR, exist_ok=True)

    safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    if not safe_name:
        safe_name = "Unknown"

    out_path = os.path.join(OUT_DIR, f"{safe_name}_certificate.png")

    # Canvas
    W, H = 1400, 1000
    img = Image.new("RGB", (W, H), (15, 23, 42))  # dark blue background
    draw = ImageDraw.Draw(img)

    # Border
    margin = 50
    draw.rectangle([margin, margin, W - margin, H - margin], outline=(255, 215, 0), width=6)
    draw.rectangle([margin + 18, margin + 18, W - margin - 18, H - margin - 18], outline=(120, 170, 255), width=2)

    # Fonts (auto fallback)
    def load_font(size):
        # Try common Windows fonts
        candidates = [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
        ]
        for p in candidates:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    title_font = load_font(70)
    big_font   = load_font(80)
    text_font  = load_font(36)
    small_font = load_font(28)

    # Text content
    title = "CERTIFICATE OF VERIFICATION"
    subtitle = "Face Award System"
    line1 = "This is to certify that"
    person = name.strip()
    line2 = "has been successfully VERIFIED by face recognition."
    line3 = "Congratulations! Your face match successfully."

    now = datetime.now()
    date_str = now.strftime("%d %b %Y  %I:%M %p")
    cert_id = now.strftime("FAS-%Y%m%d-%H%M%S")

    # Helper to center text
    def center_text(y, text, font, fill=(255, 255, 255)):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) // 2
        draw.text((x, y), text, font=font, fill=fill)

    # Layout
    center_text(120, title, title_font, fill=(255, 215, 0))
    center_text(210, subtitle, text_font, fill=(180, 210, 255))

    center_text(340, line1, text_font, fill=(235, 235, 235))
    center_text(420, person, big_font, fill=(255, 255, 255))

    center_text(540, line2, text_font, fill=(235, 235, 235))
    center_text(600, line3, text_font, fill=(170, 255, 190))

    # Footer
    draw.line([(200, 740), (W - 200, 740)], fill=(80, 120, 200), width=2)
    center_text(780, f"Date: {date_str}", small_font, fill=(210, 210, 210))
    center_text(830, f"Certificate ID: {cert_id}", small_font, fill=(210, 210, 210))

    # Save
    img.save(out_path)
    return out_path


# For testing only (run this file directly)
if __name__ == "__main__":
    path = generate_certificate("suryansa")
    print("✅ Certificate saved at:", path)
