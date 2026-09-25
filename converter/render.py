"""
render.py
Rasterizes each slide of the .pptx into a PNG image, so the video can show
the actual slide while the narration audio plays under it.

Approach: LibreOffice (headless) converts the .pptx to a single PDF, then
poppler's pdftoppm splits that PDF into one PNG per page. Both ship with
most Linux distros; on Windows/Mac install LibreOffice + poppler (see
README.md).
"""
import subprocess
import os
import glob


def render_slides_to_images(pptx_path: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)

    pdf_path = os.path.join(out_dir, "deck.pdf")
    subprocess.run(
        [
            "soffice", "--headless", "--norestore",
            "--convert-to", "pdf", "--outdir", out_dir, pptx_path,
        ],
        check=True, timeout=180,
    )
    # LibreOffice names the output after the input file, not "deck.pdf" -
    # find whatever PDF it produced and normalize the name.
    produced = glob.glob(os.path.join(out_dir, "*.pdf"))
    if not produced:
        raise RuntimeError("LibreOffice did not produce a PDF from the pptx")
    os.replace(produced[0], pdf_path)

    image_prefix = os.path.join(out_dir, "slide")
    subprocess.run(
        ["pdftoppm", "-png", "-r", "150", pdf_path, image_prefix],
        check=True, timeout=180,
    )

    images = sorted(glob.glob(f"{image_prefix}-*.png"))
    if not images:
        # some poppler versions omit the dash and zero-pad differently
        images = sorted(glob.glob(f"{image_prefix}*.png"))
    return images
