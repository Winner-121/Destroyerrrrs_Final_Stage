FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 git && rm -rf /var/lib/apt/lists/*
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir git+https://github.com/ultralytics/CLIP.git
COPY . .
# pre-download weights so first request is fast
RUN python -c "from ultralytics import YOLO; m = YOLO('yolov8s-worldv2.pt'); m.set_classes(['truck']); YOLO('yolov8s-seg.pt')"
ENV PORT=7860
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
