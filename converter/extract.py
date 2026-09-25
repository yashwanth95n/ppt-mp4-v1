"""
extract.py
Pulls the title, body text, and speaker notes off each slide of a .pptx
so we have raw material to hand to the narration script generator.
"""
from pptx import Presentation


def extract_slides(pptx_path):
    """
    Returns a list of dicts, one per slide:
    {
        "index": 0,
        "title": "Slide title text",
        "body_text": "All other text boxes, joined by newlines",
        "notes": "Speaker notes text, if any",
    }
    """
    prs = Presentation(pptx_path)
    slides = []

    for i, slide in enumerate(prs.slides):
        title = ""
        body_lines = []

        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            if not text:
                continue

            # Title placeholders conventionally have idx 0. We deliberately
            # avoid reading .type here: python-pptx tries to resolve it via
            # the slide layout and raises "shape is not a placeholder" on
            # decks from some non-PowerPoint sources (Google Slides/Canva
            # exports, etc.) where that inheritance chain doesn't resolve.
            is_title_placeholder = False
            try:
                ph = shape.placeholder_format
                if ph is not None and ph.idx == 0:
                    is_title_placeholder = True
            except Exception:
                is_title_placeholder = False
            if is_title_placeholder and not title:
                title = text
            else:
                body_lines.append(text)

        # Fallback: if no placeholder was flagged as title, use the first line
        if not title and body_lines:
            title = body_lines.pop(0)

        notes = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()

        slides.append({
            "index": i,
            "title": title or f"Slide {i + 1}",
            "body_text": "\n".join(body_lines),
            "notes": notes,
        })

    return slides


def slide_count(pptx_path):
    return len(Presentation(pptx_path).slides)
