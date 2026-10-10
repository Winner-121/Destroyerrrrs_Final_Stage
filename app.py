"""Load Safety Gate — Gradio app for Hugging Face Spaces (ZeroGPU flavor, CPU inference).

The whole pipeline runs on CPU in the main process (~120 ms per image), so visitors
never spend GPU quota. ZeroGPU requires at least one @spaces.GPU function to exist,
so a no-op one is bound to a hidden button and never called by users.
"""
import os
import time

try:
    import spaces  # must precede any CUDA-touching import on ZeroGPU
except ImportError:  # local runs without the spaces package
    class _S:
        @staticmethod
        def GPU(*a, **k):
            return (lambda f: f) if not a or not callable(a[0]) else a[0]
    spaces = _S()

import cv2
import gradio as gr
import numpy as np
from PIL import Image, ImageOps

os.environ.setdefault("LSG_DEVICE", "cpu")
from pipeline.run import analyse, get_detector  # noqa: E402

get_detector()  # load weights at startup, not on first request

STATUS_ICON = {"pass": "✅", "warn": "⚠️", "fail": "❌", "skip": "⏭️"}
VERDICT_COLOR = {"GO": "#2ea84a", "WARN": "#f0a020", "NO-GO": "#e03a3a", "CANNOT ASSESS": "#6b7680"}


def check_load(image: Image.Image):
    if image is None:
        return None, "<h2>Upload a photo of a loaded truck.</h2>", ""
    img = ImageOps.exif_transpose(image).convert("RGB")
    bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    t0 = time.perf_counter()
    r = analyse(bgr)
    ms = (time.perf_counter() - t0) * 1000
    out = cv2.cvtColor(r.pop("image"), cv2.COLOR_BGR2RGB)
    v = r["verdict"]
    rows = "".join(
        f"<tr><td>{STATUS_ICON[c['status']]} {c['name']}</td><td><b>{c['value']}</b></td>"
        f"<td>{c['status']}</td><td>{c['confidence']}</td><td>{c['reason']}</td></tr>"
        for c in r["checks"])
    html = (
        f"<div style='background:{VERDICT_COLOR.get(v, '#6b7680')};color:#fff;font-size:2rem;font-weight:700;"
        f"padding:10px 16px;border-radius:10px;text-align:center'>{v}</div>"
        f"<table style='width:100%;margin-top:10px;border-collapse:collapse'>"
        f"<tr><th align=left>Check</th><th align=left>Value</th><th align=left>Status</th><th align=left>Conf.</th><th align=left>Why</th></tr>{rows}</table>")
    meta = (f"view: {r['view']} · scale: {r['scale_source']} · {ms:.0f} ms on {r['device']} · "
            f"{r['privacy_regions_blurred']} privacy region(s) blurred"
            + (f"\n\nnotes: {' · '.join(r['notes'])}" if r["notes"] else ""))
    return Image.fromarray(out), html, meta


@spaces.GPU(duration=10)
def _gpu_noop():
    """Never called by visitors; exists only because ZeroGPU requires one decorated handler."""
    return "ok"


CSS = """
#col-container { max-width: 1000px; margin: 0 auto; }
.dark .gradio-container { color: var(--body-text-color); }
"""

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "app", "static", "examples")
EXAMPLES = sorted(os.path.join(EXAMPLES_DIR, f) for f in os.listdir(EXAMPLES_DIR)
                  if f.lower().endswith((".jpg", ".jpeg", ".png"))) if os.path.isdir(EXAMPLES_DIR) else []

with gr.Blocks(theme=gr.themes.Citrus(), css=CSS, title="Load Safety Gate") as demo:
    with gr.Column(elem_id="col-container"):
        gr.Markdown(
            "# 🚚 Load Safety Gate\n"
            "Photo of a loaded truck at the gate → **GO / WARN / NO-GO**. Checks body roll, cargo overhang and height, "
            "measured relative to the truck's own wheels and body. Plates and people are pixelated before anything is shown.\n\n"
            "Best input: a full side or rear view with the wheels visible.")
        with gr.Row():
            inp = gr.Image(type="pil", label="Truck photo (camera or upload)", sources=["upload", "webcam"])
            out = gr.Image(type="pil", label="Annotated result")
        run = gr.Button("Check load", variant="primary")
        verdict = gr.HTML()
        meta = gr.Markdown()
        if EXAMPLES:
            gr.Examples(examples=[[e] for e in EXAMPLES], inputs=[inp], outputs=[out, verdict, meta],
                        fn=check_load, cache_examples=False, label="Run the live pipeline on an example")
        run.click(fn=check_load, inputs=inp, outputs=[out, verdict, meta])
        inp.upload(fn=check_load, inputs=inp, outputs=[out, verdict, meta])
        hidden = gr.Button(visible=False)
        hidden.click(fn=_gpu_noop, outputs=gr.Textbox(visible=False))

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
