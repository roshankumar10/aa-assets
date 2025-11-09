Atlas Academy – Email Image Assets & Automation
==============================================

All email-ready images for Atlas Academy newsletters, campaigns, and automations live in this repository. Assets are optimized locally and then delivered in production via the free jsDelivr CDN, so every Gmail, Outlook, iOS, or Android inbox gets fast-loading content.

Repository layout
-----------------
```
aa-assets/
├── images/
│   ├── original/     # Source files (auto-created)
│   ├── optimized/    # Outputs from the optimizer script
│   └── *.png|*.jpg   # Working copies before optimization
└── optimize_images.py
```

Requirements
------------
- Python 3.9+
- Pillow (`pip install pillow`)
- Git access to push new image versions

Recommended workflow
--------------------
1. **Add** the raw artwork to `images/`.
2. **Run** `python3 optimize_images.py` to create email-friendly versions in `images/optimized/`.
3. **Commit + push** so jsDelivr immediately serves the new assets from `main`.
4. **Embed** the CDN URL in your email HTML.

Adding new images
-----------------
- Drop files into `images/` (PNG or JPG/JPEG are fully supported).
- Stick to lowercase descriptive names, e.g., `2026_summer_flyer.png`.
- Avoid spaces or special characters; use `_` or `-` if you need separators.

Optimizing with `optimize_images.py`
------------------------------------
```bash
python3 optimize_images.py
```
- Original files move into `images/original/` for safekeeping.
- Optimized copies land in `images/optimized/` using JPEG unless the source is a transparent PNG.
- Oversized images are scaled to a max width of 1920px while keeping the aspect ratio.
- You can rerun the script at any time; existing originals are reused so you stay lossless.

Using the CDN URLs
------------------
This folder is mirrored to the public GitHub repo `roshankumar10/aa-assets`. jsDelivr serves whatever is pushed to `main`, so keep that mirror up to date (`git push origin main`) to publish new or updated images.

Every file on `main` is instantly cached by jsDelivr.

```
https://cdn.jsdelivr.net/gh/roshankumar10/aa-assets@main/images/optimized/<file_name>
```

Example embed:
```html
<img src="https://cdn.jsdelivr.net/gh/roshankumar10/aa-assets@main/images/optimized/Atlas-Logo.jpg"
     width="180" alt="Atlas Academy logo">
```

Tips & troubleshooting
----------------------
- Need WebP or GIF output? Add it to `images/optimized/` manually and commit.
- If Pillow is missing, install it with `python3 -m pip install pillow`.
- To regenerate an image from scratch, delete its entries in `images/original/` and `images/optimized/`, then rerun the script.
