"""Run this on a CUDA Colab runtime as the remote VoxCPM2 backend.

Start with:
    uvicorn voice_clone_server:app --host 0.0.0.0 --port 7860

Set VOXCPM_TOKEN before starting if the tunnel is public.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response

from voice_clone import generate_voxcpm2, load_voxcpm2

app = FastAPI(title="Personal VoxCPM2 Voice Clone")


@app.get("/")
def health():
    return {"status": "ok", "service": "VoxCPM2", "cuda": True}


def check_token(x_voice_token: str | None) -> None:
    expected = os.getenv("VOXCPM_TOKEN", "").strip()
    if expected and x_voice_token != expected:
        raise HTTPException(status_code=401, detail="Invalid voice backend token")


@app.post("/warmup")
def warmup(x_voice_token: str | None = Header(default=None)):
    check_token(x_voice_token)
    load_voxcpm2()
    return {"status": "ready"}


@app.post("/generate")
async def generate(
    text: str = Form(...),
    reference_text: str = Form(""),
    reference_audio: UploadFile = File(...),
    x_voice_token: str | None = Header(default=None),
):
    check_token(x_voice_token)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text is required")

    suffix = Path(reference_audio.filename or "reference.wav").suffix or ".wav"
    with tempfile.TemporaryDirectory() as work_dir:
        reference_path = os.path.join(work_dir, f"reference{suffix}")
        output_path = os.path.join(work_dir, "clone.wav")
        with open(reference_path, "wb") as reference_file:
            reference_file.write(await reference_audio.read())
        try:
            generate_voxcpm2(text, reference_path, reference_text, output_path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        with open(output_path, "rb") as output_file:
            audio_bytes = output_file.read()
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=voxcpm2_clone.wav"},
        )
