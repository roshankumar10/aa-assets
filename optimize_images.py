import os
import shutil
import sys

from PIL import Image

SOURCE_DIR = "images"
ORIGINAL_DIR = os.path.join(SOURCE_DIR, "original")
OPTIMIZED_DIR = os.path.join(SOURCE_DIR, "optimized")

# Create directories if missing
os.makedirs(ORIGINAL_DIR, exist_ok=True)
os.makedirs(OPTIMIZED_DIR, exist_ok=True)

MAX_WIDTH = 1920

RASTER_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif")
SVG_EXTENSIONS = (".svg",)


def ask_output_format():
    if not sys.stdin.isatty():
        print("Non-interactive run — defaulting to JPEG")
        return "jpeg"

    print("\nOutput format for this run:")
    print("  [Enter]  JPEG (default — photos, smallest size)")
    print("  1        PNG (logos/icons with transparent backgrounds)")
    print("  2        SVG (copy .svg files only; raster files are skipped)")
    choice = input("Choice: ").strip()

    if choice == "1":
        return "png"
    if choice == "2":
        return "svg"
    return "jpeg"


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


def _has_transparency(img):
    if "A" in img.getbands():
        return True
    if img.mode == "P" and ("transparency" in img.info or "transparency" in getattr(img, "info", {})):
        return True
    return False


def _save_as_png(img, output_path):
    img = _resize_if_wide(img)
    if _has_transparency(img):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")
    img.save(output_path, format="PNG", optimize=True)


def _save_as_jpeg(img, output_path):
    img = _resize_if_wide(img)
    img = img.convert("RGB")
    img.save(output_path, format="JPEG", optimize=True, quality=82)


def optimize_image(img_path, output_path, output_format="jpeg"):
    try:
        ext = os.path.splitext(img_path)[1].lower()

        if output_format == "svg":
            if ext != ".svg":
                print(f"⏭ Skipped {img_path}: SVG output only applies to .svg files")
                return
            shutil.copy2(img_path, output_path)
            print(f"✅ Copied → {output_path}")
            return

        if ext == ".svg":
            print(f"⏭ Skipped {img_path}: choose option 2 to copy SVG files")
            return

        img = Image.open(img_path)

        if img.format == "GIF":
            _optimize_gif(img, output_path)
            img.close()
            print(f"✅ Optimized → {output_path}")
            return

        if output_format == "png":
            _save_as_png(img, output_path)
        else:
            _save_as_jpeg(img, output_path)

        img.close()
        print(f"✅ Optimized → {output_path}")
    except Exception as e:
        print(f"❌ Error processing {img_path}: {e}")


def _optimized_path(base, filename_lower, output_format):
    if filename_lower.endswith(".gif"):
        return os.path.join(OPTIMIZED_DIR, base + ".gif")
    if output_format == "png":
        return os.path.join(OPTIMIZED_DIR, base + ".png")
    if output_format == "svg":
        return os.path.join(OPTIMIZED_DIR, base + ".svg")
    return os.path.join(OPTIMIZED_DIR, base + ".jpg")


def _extensions_for_format(output_format):
    if output_format == "svg":
        return SVG_EXTENSIONS
    return RASTER_EXTENSIONS


def main():
    output_format = ask_output_format()
    extensions = _extensions_for_format(output_format)

    for filename in os.listdir(SOURCE_DIR):
        lower = filename.lower()
        if not lower.endswith(extensions):
            continue

        source_path = os.path.join(SOURCE_DIR, filename)
        if not os.path.isfile(source_path):
            continue

        original_path = os.path.join(ORIGINAL_DIR, filename)
        base = filename.rsplit(".", 1)[0]
        optimized_path = _optimized_path(base, lower, output_format)

        if not os.path.exists(original_path):
            os.rename(source_path, original_path)

        optimize_image(original_path, optimized_path, output_format)


if __name__ == "__main__":
    main()
