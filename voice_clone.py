"""Optional VoxCPM2 voice cloning backend.

The main app can still run with Edge-TTS when the optional GPU dependency is
not installed. Install requirements-gpu.txt on a CUDA host to enable cloning.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from functools import lru_cache


@lru_cache(maxsize=1)
def load_voxcpm2():
    """Load VoxCPM2 once per Streamlit process."""
    from voxcpm import VoxCPM

    return VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)


def voxcpm_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def prepare_reference_audio(input_path: str) -> str:
    """Convert reference audio to a clean 16 kHz mono WAV when ffmpeg exists."""
    fd, output_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    command = [
        "ffmpeg", "-y", "-i", input_path,
        "-ac", "1", "-ar", "16000", "-vn", output_path,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        try:
            os.remove(output_path)
        except OSError:
            pass
        return input_path
    return output_path


def generate_voxcpm2(text: str, reference_audio: str, reference_text: str, output_path: str) -> str:
    """Generate one cloned-voice WAV file using VoxCPM2."""
    import soundfile as sf

    model = load_voxcpm2()
    clean_reference = prepare_reference_audio(reference_audio)
    try:
        wav = model.generate(
            text=text,
            prompt_wav_path=clean_reference,
            prompt_text=reference_text.strip() or None,
            reference_wav_path=clean_reference,
            cfg_value=2.0,
            inference_timesteps=10,
        )
        sf.write(output_path, wav, model.tts_model.sample_rate)
        return output_path
    finally:
        if clean_reference != reference_audio:
            try:
                os.remove(clean_reference)
            except OSError:
                pass
