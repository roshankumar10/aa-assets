import os
from PIL import Image

SOURCE_DIR = "images"
ORIGINAL_DIR = os.path.join(SOURCE_DIR, "original")
OPTIMIZED_DIR = os.path.join(SOURCE_DIR, "optimized")

# Create directories if missing
os.makedirs(ORIGINAL_DIR, exist_ok=True)
os.makedirs(OPTIMIZED_DIR, exist_ok=True)

MAX_WIDTH = 1920


def _resize_if_wide(frame):
    if frame.width <= MAX_WIDTH:
        return frame
    ratio = MAX_WIDTH / frame.width
    h = max(1, int(frame.height * ratio))
    return frame.resize((MAX_WIDTH, h), Image.LANCZOS)


def _gif_frame_to_rgba(frame, source):
    """Normalize palette/other modes for resize and GIF re-encoding."""
    if frame.mode == "P":
        has_alpha = "transparency" in source.info or "transparency" in frame.info
        if has_alpha:
            return frame.convert("RGBA")
        return frame.convert("RGB")
    if frame.mode in ("RGB", "RGBA"):
        return frame
    return frame.convert("RGBA")


def _optimize_gif(im, output_path):
    n_frames = getattr(im, "n_frames", 1)
    loop = im.info.get("loop", 0)

    if n_frames <= 1:
        im.seek(0)
        frame = im.copy()
        frame = _gif_frame_to_rgba(frame, im)
        frame = _resize_if_wide(frame)
        frame.save(
            output_path,
            format="GIF",
            optimize=True,
            loop=loop,
        )
        return

    frames = []
    durations = []
    disposals = []

    for i in range(n_frames):
        im.seek(i)
        frame = im.copy()
        frame = _gif_frame_to_rgba(frame, im)
        frame = _resize_if_wide(frame)
        frames.append(frame)
        durations.append(im.info.get("duration", 100))
        disposals.append(im.info.get("disposal", im.info.get("disposal_method", 2)))

    save_kw = dict(
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=loop,
        optimize=True,
    )
    if len(set(disposals)) == 1:
        save_kw["disposal"] = disposals[0]
    else:
        save_kw["disposal"] = disposals

    frames[0].save(output_path, **save_kw)


def optimize_image(img_path, output_path):
    try:
        img = Image.open(img_path)

        if img.format == "GIF":
            _optimize_gif(img, output_path)
            img.close()
            print(f"✅ Optimized → {output_path}")
            return

        # Convert PNG with transparency as PNG, others as JPEG
        if img.format == "PNG" and "A" in img.getbands():
            img.save(output_path, format="PNG", optimize=True)
        else:
            # Resize if too big
            if img.width > MAX_WIDTH:
                ratio = MAX_WIDTH / img.width
                img = img.resize((MAX_WIDTH, int(img.height * ratio)), Image.LANCZOS)

            img = img.convert("RGB")
            img.save(output_path, format="JPEG", optimize=True, quality=82)

        print(f"✅ Optimized → {output_path}")
    except Exception as e:
        print(f"❌ Error processing {img_path}: {e}")

# Process
for filename in os.listdir(SOURCE_DIR):
    lower = filename.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif")):
        source_path = os.path.join(SOURCE_DIR, filename)
        original_path = os.path.join(ORIGINAL_DIR, filename)
        base = filename.rsplit(".", 1)[0]
        if lower.endswith(".gif"):
            optimized_path = os.path.join(OPTIMIZED_DIR, base + ".gif")
        else:
            optimized_path = os.path.join(OPTIMIZED_DIR, base + ".jpg")

        # Move original to backup
        if not os.path.exists(original_path):
            os.rename(source_path, original_path)

        # Generate optimized
        optimize_image(original_path, optimized_path)