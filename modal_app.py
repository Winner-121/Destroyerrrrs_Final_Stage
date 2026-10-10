"""Deploy Load Safety Gate on Modal (serverless, CPU, stable public URL).

    modal deploy modal_app.py        # from GitHub Actions or locally

Inference runs on CPU (~120 ms/image). One container is kept warm so the jury never
hits a cold start; cost is ~ $0.05/hour on the free Starter credits.
"""
import modal

WEIGHTS_WARMUP = (
    "from ultralytics import YOLO; "
    "m = YOLO('yolov8s-worldv2.pt'); m.set_classes(['truck']); "
    "YOLO('yolov8s-seg.pt'); print('weights ready')"
)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1", "libglib2.0-0", "git")
    .pip_install_from_requirements("requirements.txt")
    .pip_install("git+https://github.com/ultralytics/CLIP.git")   # text encoder for YOLO-World prompts
    .workdir("/root")
    .run_commands(f'python -c "{WEIGHTS_WARMUP}"')                 # download weights at build time
    .add_local_dir("pipeline", "/root/pipeline")
    .add_local_dir("app", "/root/app")
)

app = modal.App("load-safety-gate", image=image)


@app.function(cpu=2.0, memory=4096, min_containers=1, scaledown_window=900, timeout=120)
@modal.concurrent(max_inputs=4)
@modal.asgi_app()
def web():
    from app.main import app as fastapi_app
    return fastapi_app
