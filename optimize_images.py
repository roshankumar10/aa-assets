import os
from PIL import Image

SOURCE_DIR = "images"
ORIGINAL_DIR = os.path.join(SOURCE_DIR, "original")
OPTIMIZED_DIR = os.path.join(SOURCE_DIR, "optimized")

# Create directories if missing
os.makedirs(ORIGINAL_DIR, exist_ok=True)
os.makedirs(OPTIMIZED_DIR, exist_ok=True)

def optimize_image(img_path, output_path):
    try:
        img = Image.open(img_path)

        # Convert PNG with transparency as PNG, others as JPEG
        if img.format == "PNG" and "A" in img.getbands():
            img.save(output_path, format="PNG", optimize=True)
        else:
            # Resize if too big
            max_width = 1920
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

            img = img.convert("RGB")
            img.save(output_path, format="JPEG", optimize=True, quality=82)
        
        print(f"✅ Optimized → {output_path}")
    except Exception as e:
        print(f"❌ Error processing {img_path}: {e}")

# Process
for filename in os.listdir(SOURCE_DIR):
    if filename.lower().endswith((".png", ".jpg", ".jpeg")):
        source_path = os.path.join(SOURCE_DIR, filename)
        original_path = os.path.join(ORIGINAL_DIR, filename)
        optimized_path = os.path.join(OPTIMIZED_DIR, filename.rsplit(".", 1)[0] + ".jpg")

        # Move original to backup
        if not os.path.exists(original_path):
            os.rename(source_path, original_path)

        # Generate optimized
        optimize_image(original_path, optimized_path)