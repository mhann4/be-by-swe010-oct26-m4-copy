import streamlit as st
import os
import subprocess
import math
import concurrent.futures
import asyncio
import edge_tts
import time
import shutil
import gc
import threading
import base64
from voice_clone import generate_voxcpm2, voxcpm_available
# ─────────────────────────────────────────────
# Timer Utility
# ─────────────────────────────────────────────

def format_time(seconds):
    """Format seconds into mm:ss or mm:ss.ms format."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    ms = int((seconds % 1) * 10)
    if mins > 0:
        return f"{mins}:{secs:02d}"
    return f"{secs}.{ms}s"


# ─────────────────────────────────────────────
# TTS Voices, Recap Styles, and Emotions
# ─────────────────────────────────────────────

@st.cache_resource
def get_voices():
    return [
        {"id": "v1", "name": "V1 ♂", "gender": "Male"},
        {"id": "v2", "name": "V2 ♀", "gender": "Female"},
        {"id": "v3", "name": "V3 ♂", "gender": "Male"},
        {"id": "v4", "name": "V4 ♂", "gender": "Male"},
        {"id": "v5", "name": "V5 ♂", "gender": "Male"},
        {"id": "v6", "name": "V6 ♀", "gender": "Female"},
        {"id": "v7", "name": "V7 ♂", "gender": "Male"},
        {"id": "v8", "name": "V8 ♀", "gender": "Female"},
        {"id": "v9", "name": "V9 ♂", "gender": "Male"},
        {"id": "v10", "name": "V10 ♀", "gender": "Female"},
        {"id": "v11", "name": "V11 ♀", "gender": "Female"},
        {"id": "v12", "name": "V12 ♂", "gender": "Male"},
        {"id": "v13", "name": "V13 ♀", "gender": "Female"},
        {"id": "v14", "name": "V14 ♂", "gender": "Male"},
        {"id": "v15", "name": "V15 ♀", "gender": "Female"},
        {"id": "v16", "name": "V16 ♀", "gender": "Female"},
        {"id": "v17", "name": "V17 ♂", "gender": "Male"},
        {"id": "v18", "name": "V18 ♂", "gender": "Male"},
        {"id": "v19", "name": "V19 ♀", "gender": "Female"}
    ]

@st.cache_resource
def get_recap_styles():
    return [
        {"id": "Normal", "name": "ပုံမှန်အသံ", "speed": 0, "pitch": 0},
        {"id": "NyoGyi_25", "name": "ကျားကြီး ၁", "speed": 0, "pitch": 25},
        {"id": "NyoGyi_35", "name": "ကျားကြီး ၂", "speed": 0, "pitch": 35},
        {"id": "NyoGyi_45", "name": "ကျားကြီး ၃", "speed": 0, "pitch": 45},
        {"id": "Nilar_40", "name": "နီလာ ချွဲသံ", "speed": 0, "pitch": 40},
        {"id": "Combo_15", "name": "ပေါင်းစပ် ၁၅", "speed": 15, "pitch": 15},
        {"id": "Combo_30", "name": "ပေါင်းစပ် ၃၀", "speed": 30, "pitch": 30},
        {"id": "Combo_50", "name": "ပေါင်းစပ် ၅၀", "speed": 50, "pitch": 50},
        {"id": "Pitch_20", "name": "အသံသေး ၂၀", "speed": 0, "pitch": 20},
        {"id": "Pitch_50", "name": "အသံသေး ၅၀", "speed": 0, "pitch": 50}
    ]

@st.cache_resource
def get_emotions():
    return [
        {"id": "EXCITING", "name": "စိတ်လှုပ်ရှား 🤩", "s": 15, "p": 10},
        {"id": "CALM", "name": "တည်ငြိမ် 😌", "s": -10, "p": -5},
        {"id": "PROFESSIONAL", "name": "သတင်း 💼", "s": 0, "p": -2},
        {"id": "NARRATIVE", "name": "ဇာတ်ကြောင်း 📖", "s": -5, "p": 0},
        {"id": "HAPPY", "name": "ပျော်ရွှင် 😊", "s": 10, "p": 15},
        {"id": "SERIOUS", "name": "လေးနက် 😠", "s": -5, "p": -10},
        {"id": "WHISPER", "name": "တီးတိုး 🤫", "s": -15, "p": -20},
        {"id": "SAD", "name": "ဝမ်းနည်း 😢", "s": -15, "p": -15},
        {"id": "SARCASTIC", "name": "ရွဲ့ပြော 🙄", "s": -10, "p": 5},
        {"id": "ANGRY", "name": "ဒေါသထွက် 🤬", "s": 20, "p": -10},
        {"id": "FEAR", "name": "ကြောက်လန့် 😨", "s": 10, "p": 20}
    ]

VOICES = get_voices()
RECAP_STYLES = get_recap_styles()
EMOTIONS = get_emotions()

st.set_page_config(page_title="Video & Text Processor", layout="wide")


# ─────────────────────────────────────────────
# SRT Subtitle Generator
# ─────────────────────────────────────────────

class SmartSubMaker:
    """Generate SRT subtitles proportional to text length and total video duration."""

    def __init__(self, full_text, duration_seconds):
        self.full_text = full_text.strip().replace('\n', ' ')
        self.duration_seconds = duration_seconds
        self.max_chars_per_line = 60

    def safe_myanmar_split(self, text):
        """Split Myanmar text safely without breaking syllables.
        Checks Unicode range \u102B-\u103E and \u105E-\u105F for medials/vowels/signs."""
        chunks = []
        words = text.split(' ')
        current_chunk = ""
        for word in words:
            if not word:
                continue
            if current_chunk and len(current_chunk) + len(word) + 1 > self.max_chars_per_line:
                chunks.append(current_chunk.strip())
                current_chunk = word + " "
            else:
                current_chunk += word + " "
        while len(current_chunk) > self.max_chars_per_line + 20:
            split_idx = self.max_chars_per_line
            while split_idx < len(current_chunk):
                char = current_chunk[split_idx]
                if '\u102B' <= char <= '\u103E' or '\u105E' <= char <= '\u105F':
                    split_idx += 1
                else:
                    break
            chunks.append(current_chunk[:split_idx].strip())
            current_chunk = current_chunk[split_idx:]
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        return chunks

    def generate_subs(self):
        """Generate full SRT text with proportional timestamps."""
        if not self.full_text or self.duration_seconds <= 0:
            return "1\n00:00:00,000 --> 00:00:05,000\n[အသံထွက်နေပါသည်...]\n\n"

        # Split by Myanmar period (။) first
        raw_sentences = [s.strip() + "။" for s in self.full_text.split("။") if s.strip()]
        if not raw_sentences:
            raw_sentences = [self.full_text]

        # Further split long sentences by space within char limit
        final_chunks = []
        for rs in raw_sentences:
            split_parts = self.safe_myanmar_split(rs)
            final_chunks.extend(split_parts)

        total_chars = sum(len(c) for c in final_chunks)
        if total_chars == 0:
            total_chars = 1

        srt_text = ""
        current_time = 0.0
        for i, chunk in enumerate(final_chunks, 1):
            char_ratio = len(chunk) / total_chars
            chunk_duration = self.duration_seconds * char_ratio
            start_time = current_time
            end_time = current_time + chunk_duration
            srt_text += f"{i}\n"
            srt_text += f"{self._format_time(start_time)} --> {self._format_time(end_time)}\n"
            srt_text += f"{chunk}\n\n"
            current_time = end_time
        return srt_text

    def _format_time(self, seconds_float):
        """Format seconds to SRT timestamp HH:MM:SS,mmm."""
        hours = int(seconds_float // 3600)
        minutes = int((seconds_float % 3600) // 60)
        secs = int(seconds_float % 60)
        millis = int(round((seconds_float - int(seconds_float)) * 1000))
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def count_paragraphs(text):
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return paragraphs


def make_output_basename(uploaded_name):
    original_name = os.path.splitext(os.path.basename(uploaded_name))[0]
    return f"BE_{original_name[:20].replace(' ', '_')}"


# ─────────────────────────────────────────────
# TTS Generation
# ─────────────────────────────────────────────

async def generate_all_tts(paragraphs, audio_dir, voice_id, speed, pitch,
                           reference_audio=None, reference_text=""):
    """Generate TTS for all paragraphs in parallel."""
    if voice_id == "custom_voxcpm2":
        if not reference_audio:
            raise ValueError("Custom voice reference audio is missing.")
        # Keep VoxCPM2 generation sequential: one GPU model is shared by all
        # paragraphs and concurrent calls can exhaust VRAM or corrupt output.
        for i, paragraph in enumerate(paragraphs):
            generate_voxcpm2(
                paragraph,
                reference_audio,
                reference_text,
                os.path.join(audio_dir, f"audio_{i}.wav"),
            )
        return

    tasks = []
    for i, paragraph in enumerate(paragraphs):
        tasks.append(generate_tts_async(paragraph, os.path.join(audio_dir, f"audio_{i}.mp3"), voice_id, speed, pitch))
    await asyncio.gather(*tasks)


VOICE_MAP = {
    "v1": "my-MM-ThihaNeural",
    "v2": "my-MM-NilarNeural",
    "v3": "it-IT-GiuseppeMultilingualNeural",
    "v4": "en-AU-WilliamMultilingualNeural",
    "v5": "en-US-AndrewMultilingualNeural",
    "v6": "en-US-AvaMultilingualNeural",
    "v7": "en-US-BrianMultilingualNeural",
    "v8": "en-US-EmmaMultilingualNeural",
    "v9": "fr-FR-RemyMultilingualNeural",
    "v10": "fr-FR-VivienneMultilingualNeural",
    "v11": "de-DE-SeraphinaMultilingualNeural",
    "v12": "de-DE-FlorianMultilingualNeural",
    "v13": "pt-BR-ThalitaMultilingualNeural",
    "v14": "ko-KR-HyunsuMultilingualNeural",
    "v15": "en-US-JennyNeural",
    "v16": "en-US-AriaNeural",
    "v17": "en-US-GuyNeural",
    "v18": "en-GB-RyanNeural",
    "v19": "en-GB-SoniaNeural"
}

ENGLISH_VOICE_IDS = {"v4", "v5", "v6", "v7", "v8", "v15", "v16", "v17", "v18", "v19"}
ENGLISH_VOICE_LABELS = {
    "v4": "William (AU)",
    "v5": "Andrew (US)",
    "v6": "Ava (US)",
    "v7": "Brian (US)",
    "v8": "Emma (US)",
    "v15": "Jenny (US)",
    "v16": "Aria (US)",
    "v17": "Guy (US)",
    "v18": "Ryan (GB)",
    "v19": "Sonia (GB)",
}

MYANMAR_VOICE_IDS = {"v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10", "v11", "v12", "v13", "v14"}

MYANMAR_VOICE_LABELS = {
    "v1": "V1 ♂ Thiha (MM)",
    "v2": "V2 ♀ Nilar (MM)",
    "v3": "V3 ♂ Giuseppe (IT)",
    "v4": "V4 ♂ William (AU)",
    "v5": "V5 ♂ Andrew (US)",
    "v6": "V6 ♀ Ava (US)",
    "v7": "V7 ♂ Brian (US)",
    "v8": "V8 ♀ Emma (US)",
    "v9": "V9 ♂ Remy (FR)",
    "v10": "V10 ♀ Vivienne (FR)",
    "v11": "V11 ♀ Seraphina (DE)",
    "v12": "V12 ♂ Florian (DE)",
    "v13": "V13 ♀ Thalita (PT-BR)",
    "v14": "V14 ♂ Hyunsu (KO)",
}

ENGLISH_VOICE_LABELS = {
    "v4": "William (AU) ♂",
    "v5": "Andrew (US) ♂",
    "v6": "Ava (US) ♀",
    "v7": "Brian (US) ♂",
    "v8": "Emma (US) ♀",
    "v15": "Jenny (US) ♀",
    "v16": "Aria (US) ♀",
    "v17": "Guy (US) ♂",
    "v18": "Ryan (GB) ♂",
    "v19": "Sonia (GB) ♀",
}

RECAP_STYLE_EN = {
    "ပုံမှန်အသံ": "Normal",
    "ကျားကြီး ၁": "Deep Male 1",
    "ကျားကြီး ၂": "Deep Male 2",
    "ကျားကြီး ၃": "Deep Male 3",
    "နီလာ ချွဲသံ": "Soft Voice",
    "ပေါင်းစပ် ၁၅": "Combo Light",
    "ပေါင်းစပ် ၃၀": "Combo Medium",
    "ပေါင်းစပ် ၅၀": "Combo Strong",
    "အသံသေး ၂၀": "High Pitch Light",
    "အသံသေး ၅၀": "High Pitch Strong",
}

EMOTION_EN = {
    "စိတ်လှုပ်ရှား 🤩": "Exciting 🤩",
    "တည်ငြိမ် 😌": "Calm 😌",
    "သတင်း 💼": "News 💼",
    "ဇာတ်ကြောင်း 📖": "Narrative 📖",
    "ပျော်ရွှင် 😊": "Happy 😊",
    "လေးနက် 😠": "Serious 😠",
    "တီးတိုး 🤫": "Whisper 🤫",
    "ဝမ်းနည်း 😢": "Sad 😢",
    "ရွဲ့ပြော 🙄": "Sarcastic 🙄",
    "ဒေါသထွက် 🤬": "Angry 🤬",
    "ကြောက်လန့် 😨": "Fear 😨",
}

async def generate_tts_async(text, output_path, voice_id, speed, pitch):
    """Async TTS generation for parallel execution."""
    real_voice = VOICE_MAP.get(voice_id, "my-MM-ThihaNeural")
    rate_str = f"+{speed}%" if speed >= 0 else f"{speed}%"
    pitch_str = f"+{pitch}Hz" if pitch >= 0 else f"{pitch}Hz"
    communicate = edge_tts.Communicate(text, real_voice, rate=rate_str, pitch=pitch_str)
    await communicate.save(output_path)
    return output_path


# ─────────────────────────────────────────────
# Probe Helpers
# ─────────────────────────────────────────────

def get_video_duration(video_path):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout.strip())


def get_video_resolution(video_path):
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
           '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', video_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    res = result.stdout.strip().split('x')
    w, h = int(res[0]), int(res[1])
    return w, h


def get_audio_duration(audio_path):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout.strip())


# ─────────────────────────────────────────────
# Step 1: Split video into segments (video only, no audio)
# ─────────────────────────────────────────────

def split_video(video_path, num_segments, output_dir):
    """Split video into segments using fast copy (instant, no re-encoding).
    Audio is stripped to avoid conflicts."""
    duration = get_video_duration(video_path)
    segment_duration = duration / num_segments
    segments = []
    for i in range(num_segments):
        start_time = i * segment_duration
        output_path = os.path.join(output_dir, f"segment_{i}.mp4")
        cmd = ['ffmpeg', '-y', '-ss', str(start_time), '-t', str(segment_duration),
               '-i', video_path, '-c:v', 'copy', '-an',
               '-avoid_negative_ts', 'make_zero', output_path]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        segments.append(output_path)
    return segments, segment_duration


# ─────────────────────────────────────────────
# Step 2: Speed-adjust each segment to match TTS audio
# ─────────────────────────────────────────────

def speed_adjust_segment(index, video_segment, audio_path, adjusted_dir):
    """Speed-adjust VIDEO ONLY to match TTS audio duration.
    TTS audio is kept at original speed (no atempo).
    Returns the path to the adjusted segment (video+audio combined).
    Cleans up the original segment after success."""
    audio_duration = get_audio_duration(audio_path)
    orig_duration = get_video_duration(video_segment)
    output_path = os.path.join(adjusted_dir, f"adjusted_{index}.mp4")

    # Target video duration is rounded up to the nearest 0.5s increment
    # relative to the audio duration (ensuring a buffer of 0 to 0.5s).
    # This prevents audio truncation while keeping the buffer small.
    target_video_duration = math.ceil(audio_duration * 2) / 2
    
    # Ensure the video is at least as long as the audio (handle float precision)
    if target_video_duration < audio_duration:
        target_video_duration = audio_duration
        
    speed_factor = target_video_duration / orig_duration

    # Use a simpler filter complex that only touches video PTS.
    # We map audio directly (1:a) to ensure the TTS audio duration is strictly preserved.
    # We do NOT use -shortest because we want the video to be slightly longer (0-0.5s) than the audio.
    cmd = [
        'ffmpeg', '-y',
        '-i', video_segment,
        '-i', audio_path,
        '-filter_complex', f"[0:v]setpts={speed_factor}*PTS[v]",
        '-map', '[v]',
        '-map', '1:a',
        '-c:v', 'libx264', '-preset', 'ultrafast',
        '-c:a', 'aac',
        output_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0 and os.path.exists(output_path):
        if os.path.exists(video_segment):
            os.remove(video_segment)
        return output_path
    else:
        raise Exception(f"Speed adjust failed for segment {index}: {result.stderr}")


# ─────────────────────────────────────────────
# Step 3: Merge all speed-adjusted segments
# ─────────────────────────────────────────────

def merge_speed_adjusted_segments(adjusted_segments, output_path):
    """Merge all speed-adjusted segments into a single video."""
    concat_file = output_path + "_concat.txt"
    with open(concat_file, 'w') as f:
        for seg in adjusted_segments:
            f.write(f"file '{os.path.abspath(seg)}'\n")
    cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
           '-i', concat_file, '-c', 'copy', output_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if os.path.exists(concat_file):
        os.remove(concat_file)
    if result.returncode != 0:
        raise Exception(f"Merge speed-adjusted segments failed: {result.stderr}")
    for seg in adjusted_segments:
        if os.path.exists(seg):
            os.remove(seg)



# ─────────────────────────────────────────────
# Step 5: Apply cycle repeat to a single chunk
# ─────────────────────────────────────────────

def build_cycle_filter(video_path, audio_path, chunk_duration,
                       freeze1_dur, freeze2_dur,
                       freeze1_zoom, freeze2_zoom, zoom_dur):
    """Build FFmpeg filter complex for cycle repeat on a chunk."""
    fps = 24
    cycle_duration = freeze1_dur + freeze2_dur
    num_cycles = math.ceil(chunk_duration / cycle_duration)

    # Use original resolution
    width, height = get_video_resolution(video_path)
    res_str = f"{width}x{height}"

    def make_zoom_filter(zoom_dur, total_dur, zoom_type):
        total_frames = max(int(total_dur * fps), 1)
        zoom_frames = max(int(zoom_dur * fps), 1)
        # Cap zoom_frames at total_frames to avoid overflow
        z_frames = min(zoom_frames, total_frames)
        
        if zoom_type == "Zoom In":
            # Zoom from 1.0 to 1.15 over z_frames, then stay at 1.15
            return (f"zoompan=z='if(lte(on,{z_frames}),min(1+0.15*on/{z_frames},1.15),1.15)':"
                    f"d={total_frames}:s={res_str}:fps={fps}")
        elif zoom_type == "Zoom Out":
            # Zoom from 1.15 to 1.0 over z_frames, then stay at 1.0
            return (f"zoompan=z='if(lte(on,{z_frames}),max(1.15-0.15*on/{z_frames},1.0),1.0)':"
                    f"d={total_frames}:s={res_str}:fps={fps}")
        return None

    f1_z = make_zoom_filter(zoom_dur, freeze1_dur, freeze1_zoom) if freeze1_zoom != "None" else None
    f2_z = make_zoom_filter(zoom_dur, freeze2_dur, freeze2_zoom) if freeze2_zoom != "None" else None

    filter_parts = []
    concat_inputs = []

    for i in range(num_cycles):
        curr = i * cycle_duration

        # Play section


        # Freeze 1
        f1_start = curr
        if f1_start < chunk_duration:
            f1_end = min(f1_start + freeze1_dur, chunk_duration)
            f1_actual_dur = f1_end - f1_start
            if f1_actual_dur > 0:
                filter_parts.append(
                    f"[0:v]trim=start={f1_start}:end={f1_end},setpts=PTS-STARTPTS,"
                    f"loop=loop={int(f1_actual_dur * fps)}:size=1:start=0[vf1_{i}];")
                if f1_z:
                    filter_parts.append(f"[vf1_{i}]{f1_z}[vf1z_{i}];")
                    concat_inputs.append(f"[vf1z_{i}]")
                else:
                    concat_inputs.append(f"[vf1_{i}]")

        # Freeze 2
        f2_start = curr + freeze1_dur
        if f2_start < chunk_duration:
            f2_end = min(f2_start + freeze2_dur, chunk_duration)
            f2_actual_dur = f2_end - f2_start
            if f2_actual_dur > 0:
                filter_parts.append(
                    f"[0:v]trim=start={f2_start}:end={f2_end},setpts=PTS-STARTPTS,"
                    f"loop=loop={int(f2_actual_dur * fps)}:size=1:start=0[vf2_{i}];")
                if f2_z:
                    filter_parts.append(f"[vf2_{i}]{f2_z}[vf2z_{i}];")
                    concat_inputs.append(f"[vf2z_{i}]")
                else:
                    concat_inputs.append(f"[vf2_{i}]")

    filter_str = "".join(filter_parts)
    filter_str += "".join(concat_inputs) + f"concat=n={len(concat_inputs)}:v=1:a=0[vout]"
    
    return filter_str


def process_chunk_with_retry(index, chunk_path, chunk_duration, output_dir,
                            play_dur, freeze1_dur, freeze2_dur,
                            freeze1_zoom, freeze2_zoom, zoom_dur, retries=2):
    """Process a single chunk with FFmpeg filter complex. Retries on failure."""
    output_path = os.path.join(output_dir, f"processed_{index}.mp4")
    filter_str = build_cycle_filter(chunk_path, chunk_path, chunk_duration,
                                    play_dur, freeze1_dur, freeze2_dur,
                                    freeze1_zoom, freeze2_zoom, zoom_dur)
    
    cmd = [
        'ffmpeg', '-y', '-i', chunk_path,
        '-filter_complex', filter_str,
        '-map', '[vout]', '-map', '0:a',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-c:a', 'copy', output_path
    ]

    for attempt in range(retries + 1):
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0 and os.path.exists(output_path):
            if os.path.exists(chunk_path):
                os.remove(chunk_path)
            return output_path
        time.sleep(1)
    
    raise Exception(f"Chunk {index} failed after {retries} retries: {result.stderr}")


def merge_videos(video_list, output_path):
    valid_videos = [v for v in video_list if v is not None and os.path.exists(v)]
    if not valid_videos:
        raise Exception("No valid segments to merge.")
    concat_file = "concat_list.txt"
    with open(concat_file, 'w') as f:
        for video in valid_videos:
            f.write(f"file '{os.path.abspath(video)}'\n")
    cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
           '-i', concat_file, '-c', 'copy', output_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    if os.path.exists(concat_file):
        os.remove(concat_file)
    if result.returncode != 0:
        raise Exception(f"Merge Error: {result.stderr}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    st.title("🎬 Video & Text Processor with TTS")

    # ─────────────────────────────────────────────
    # Language Toggle
    # ─────────────────────────────────────────────
    if "language" not in st.session_state:
        st.session_state.language = "မြန်မာ"

    st.session_state.language = st.segmented_control(
        "Language / ဘာသာစကား",
        options=["မြန်မာ", "English"],
        default=st.session_state.language,
    )

    lang = st.session_state.language
    is_en = lang == "English"

    st.markdown("---")

    # ─────────────────────────────────────────────
    # Settings Section (Main UI)
    # ─────────────────────────────────────────────
    st.header("⚙️ Settings" if not is_en else "⚙️ Settings")

    # Build voice list based on language
    if is_en:
        voice_options = [ENGLISH_VOICE_LABELS[v["id"]] for v in VOICES if v["id"] in ENGLISH_VOICE_IDS]
    else:
        voice_options = [MYANMAR_VOICE_LABELS[v["id"]] for v in VOICES if v["id"] in MYANMAR_VOICE_IDS]

    # Build recap style and emotion labels
    if is_en:
        style_options = [RECAP_STYLE_EN.get(s["name"], s["name"]) for s in RECAP_STYLES]
        emotion_options = [EMOTION_EN.get(e["name"], e["name"]) for e in EMOTIONS]
    else:
        style_options = [s["name"] for s in RECAP_STYLES]
        emotion_options = [e["name"] for e in EMOTIONS]

    # UI labels
    label_voice = "Voice" if is_en else "အသံ ရွေးပါ"
    label_style = "Recap Style" if is_en else "အသံ ဟန်"
    label_emotion = "Emotion" if is_en else "စိတ်ခံစားမှု"
    label_preset = "📊 Preset → Speed: {speed}%, Pitch: {pitch}Hz"
    label_final = "📊 Final → Speed: {speed}%, Pitch: {pitch}Hz"
    label_speed = "Speed (%)" if is_en else "အမြန်နှုန်း (%)"
    label_pitch = "Pitch (Hz)" if is_en else "အသံ အနိမ့်အမြင့် (Hz)"
    label_text = "📝 Enter Text" if is_en else "📝 စာသား ထည့်ပါ"
    label_video = "🎥 Upload Video" if is_en else "🎥 ဗီဒီယို တင်ပါ"
    label_start = "🚀 Start Processing" if is_en else "🚀 Processing စတင်ပါ"
    label_info = "📊 Paragraphs: {para} | Characters: {char}"
    label_error = "❌ Provide text and video." if is_en else "❌ စာသား နှင့် ဗီဒီယို ထည့်ပါ။"

    # --- Voice, Recap Style, Emotion: 3-column button grid ---

    # Helper: get voice labels in order
    def _get_voice_labels():
        if is_en:
            return [ENGLISH_VOICE_LABELS[v["id"]] for v in VOICES if v["id"] in ENGLISH_VOICE_IDS]
        return [MYANMAR_VOICE_LABELS[v["id"]] for v in VOICES if v["id"] in MYANMAR_VOICE_IDS]

    def _get_voice_ids():
        if is_en:
            return [v["id"] for v in VOICES if v["id"] in ENGLISH_VOICE_IDS]
        return [v["id"] for v in VOICES if v["id"] in MYANMAR_VOICE_IDS]

    voice_labels = _get_voice_labels()
    voice_ids = _get_voice_ids()

    # Initialize selections in session state with defaults
    if "sel_voice" not in st.session_state:
        st.session_state.sel_voice = voice_ids[0]
    if "sel_style" not in st.session_state:
        st.session_state.sel_style = RECAP_STYLES[0]["id"]
    if "sel_emotion" not in st.session_state:
        st.session_state.sel_emotion = EMOTIONS[0]["id"]

    # When language changes, reset selections to defaults
    lang_key = "en" if is_en else "my"
    if "sel_voice_lang" not in st.session_state or st.session_state.sel_voice_lang != lang_key:
        st.session_state.sel_voice = voice_ids[0]
        st.session_state.sel_voice_lang = lang_key

    # --- Voice Grid ---
    st.markdown(f"**{label_voice}**")
    voice_col_count = 3
    voice_rows = math.ceil(len(voice_labels) / voice_col_count)
    for row_idx in range(voice_rows):
        cols = st.columns(voice_col_count)
        for col_idx in range(voice_col_count):
            idx = row_idx * voice_col_count + col_idx
            if idx < len(voice_labels):
                with cols[col_idx]:
                    is_selected = (st.session_state.sel_voice == voice_ids[idx])
                    btn_label = voice_labels[idx]
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(btn_label, key=f"voice_{voice_ids[idx]}", type=btn_type, use_container_width=True):
                        st.session_state.sel_voice = voice_ids[idx]
                        st.rerun()

    # --- Optional VoxCPM2 custom voice ---
    with st.expander("🧬 Custom Voice Clone (VoxCPM2)" if is_en else "🧬 ကိုယ်ပိုင်အသံ Clone (VoxCPM2)"):
        st.caption(
            "Runs on the GPU host where this app is deployed. A 3–10 second reference "
            "clip and its exact transcript work best."
            if is_en else
            "ဒီ feature က app run နေတဲ့ GPU host ပေါ်မှာ VoxCPM2 ကို run ပါမယ်။ "
            "3–10 စက္ကန့် reference အသံနဲ့ အဲဒီအသံထဲက စာသားအတိအကျကို ထည့်ပါ။"
        )
        if not voxcpm_available():
            st.warning(
                "VoxCPM2 GPU backend မတွေ့ပါ။ requirements-gpu.txt ကို install လုပ်ပြီး "
                "CUDA GPU host ပေါ်မှာ app ကို run ပါ။"
            )
        clone_reference_audio = st.file_uploader(
            "Reference voice (WAV/MP3/FLAC)" if is_en else "Reference အသံ (WAV/MP3/FLAC)",
            type=["wav", "mp3", "flac", "m4a"],
            key="clone_reference_audio",
        )
        clone_reference_text = st.text_area(
            "Exact words spoken in the reference clip" if is_en else "Reference အသံထဲမှာ ပြောထားတဲ့စာသားအတိအကျ",
            height=90,
            key="clone_reference_text",
        )
        use_custom_voice = st.checkbox(
            "Use this cloned voice for the video" if is_en else "ဒီ clone အသံကို ဗီဒီယိုမှာသုံးမယ်",
            key="use_custom_voice",
        )
        if use_custom_voice:
            if clone_reference_audio is None:
                st.info("Reference audio တင်ပြီး checkbox ကို ပြန်ရွေးပါ။")
            elif not clone_reference_text.strip():
                st.info("Reference audio ထဲက စာသားအတိအကျ ထည့်ပါ။")
            else:
                st.success("Custom VoxCPM2 voice ကို ရွေးထားပါတယ်။")

    # --- Recap Style Grid ---
    st.markdown(f"**{label_style}**")
    style_labels = [RECAP_STYLE_EN.get(s["name"], s["name"]) if is_en else s["name"] for s in RECAP_STYLES]
    style_col_count = 3
    style_rows = math.ceil(len(style_labels) / style_col_count)
    for row_idx in range(style_rows):
        cols = st.columns(style_col_count)
        for col_idx in range(style_col_count):
            idx = row_idx * style_col_count + col_idx
            if idx < len(style_labels):
                with cols[col_idx]:
                    is_selected = (st.session_state.sel_style == RECAP_STYLES[idx]["id"])
                    btn_label = style_labels[idx]
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(btn_label, key=f"style_{RECAP_STYLES[idx]['id']}", type=btn_type, use_container_width=True):
                        st.session_state.sel_style = RECAP_STYLES[idx]["id"]
                        st.rerun()

    # --- Emotion Grid ---
    st.markdown(f"**{label_emotion}**")
    emotion_labels = [EMOTION_EN.get(e["name"], e["name"]) if is_en else e["name"] for e in EMOTIONS]
    emotion_col_count = 3
    emotion_rows = math.ceil(len(emotion_labels) / emotion_col_count)
    for row_idx in range(emotion_rows):
        cols = st.columns(emotion_col_count)
        for col_idx in range(emotion_col_count):
            idx = row_idx * emotion_col_count + col_idx
            if idx < len(emotion_labels):
                with cols[col_idx]:
                    is_selected = (st.session_state.sel_emotion == EMOTIONS[idx]["id"])
                    btn_label = emotion_labels[idx]
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(btn_label, key=f"emotion_{EMOTIONS[idx]['id']}", type=btn_type, use_container_width=True):
                        st.session_state.sel_emotion = EMOTIONS[idx]["id"]
                        st.rerun()

    # Map selected to voice_id, style_data, emotion_data
    voice_id = "custom_voxcpm2" if use_custom_voice else st.session_state.sel_voice
    style_data = next((s for s in RECAP_STYLES if s["id"] == st.session_state.sel_style), RECAP_STYLES[0])
    emotion_data = next((e for e in EMOTIONS if e["id"] == st.session_state.sel_emotion), EMOTIONS[0])

    preset_speed = style_data["speed"] + emotion_data["s"]
    preset_pitch = style_data["pitch"] + emotion_data["p"]
    st.caption(f"📊 Preset → Speed: {preset_speed}%, Pitch: {preset_pitch}Hz")

    # Row 2: Speed & Pitch Sliders
    st.markdown("**🎛️ Adjust Speed & Pitch**")
    slider1, slider2 = st.columns(2)
    with slider1:
        final_speed = st.slider(label_speed, min_value=-50, max_value=100, value=preset_speed, step=1)
    with slider2:
        final_pitch = st.slider(label_pitch, min_value=-50, max_value=100, value=preset_pitch, step=1)

    st.caption(f"📊 Final → Speed: {final_speed}%, Pitch: {final_pitch}Hz")
    st.markdown("---")

    # Row 3: Text Input & Video Upload
    input_col, video_col = st.columns(2)
    with input_col:
        text_input = st.text_area(label_text, height=200)
        if text_input:
            paragraphs = count_paragraphs(text_input)
            st.info(f"📊 Paragraphs: {len(paragraphs)} | Characters: {len(text_input)}")
    with video_col:
        video_file = st.file_uploader(label_video, type=["mp4", "mov", "avi"])

    # Initialize session state for tracking
    if 'processing_active' not in st.session_state:
        st.session_state.processing_active = False

    # Start button logic
    if st.button(label_start) and not st.session_state.processing_active:

        if not text_input or not video_file:
            st.error(label_error)
            return
        if use_custom_voice and (clone_reference_audio is None or not clone_reference_text.strip()):
            st.error(
                "Reference audio နဲ့ reference transcript နှစ်ခုလုံးလိုပါတယ်။"
                if not is_en else
                "Custom voice requires reference audio and its exact transcript."
            )
            return
        
        st.session_state.processing_active = True
        
        # Save inputs to session state
        st.session_state.inputs = {
            "text": text_input,
            "voice_id": voice_id,
            "final_speed": final_speed,
            "final_pitch": final_pitch,
            "reference_text": clone_reference_text if use_custom_voice else "",

        }
        st.session_state.output_basename = make_output_basename(video_file.name)

        # Setup temp directories
        temp_dir = "temp_processing"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

        st.session_state.dirs = {
            "temp": temp_dir,
            "audio": os.path.join(temp_dir, "audio"),
            "video": os.path.join(temp_dir, "video"),
            "adjusted": os.path.join(temp_dir, "adjusted"),
        }
        for d in st.session_state.dirs.values():
            os.makedirs(d, exist_ok=True)

        reference_audio_path = None
        if use_custom_voice and clone_reference_audio is not None:
            reference_audio_path = os.path.join(st.session_state.dirs["audio"], "voice_reference")
            with open(reference_audio_path, "wb") as f:
                f.write(clone_reference_audio.getbuffer())
            st.session_state.inputs["reference_audio"] = reference_audio_path

        video_path = os.path.join(st.session_state.dirs["video"], "input_video.mp4")
        st.session_state.video_path = video_path

        with open(video_path, "wb") as f:
            while chunk := video_file.read(8192):
                f.write(chunk)

        # Display status and progress
        status = st.status("Processing video...", expanded=True)
        status.write("Starting video processing...")
        progress_bar = status.progress(0, text="Initializing...")
        step_status_placeholder = status.empty()
        progress_detail = status.empty()
        timer_placeholder = status.empty()

        total_start = time.time()

        try:
            inputs = st.session_state.inputs
            dirs = st.session_state.dirs
            video_path = st.session_state.video_path
            paragraphs = count_paragraphs(inputs["text"])
            num_paragraphs = len(paragraphs)

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # STEP 1+2: Pre-process Video + TTS + Split (PARALLEL)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            step_status_placeholder.markdown("**Step 1/3:** Pre-processing video & generating TTS...")
            progress_detail.markdown("Initializing...")
            step_start = time.time()

            progress_detail.markdown(f"🔊 Generating {num_paragraphs} TTS files in parallel...")
            asyncio.run(generate_all_tts(
                paragraphs,
                dirs["audio"],
                inputs["voice_id"],
                inputs["final_speed"],
                inputs["final_pitch"],
                inputs.get("reference_audio"),
                inputs.get("reference_text", ""),
            ))
            progress_detail.markdown(f"✅ TTS complete ({num_paragraphs}/{num_paragraphs})")

            progress_detail.markdown(f"✂️ Splitting video into {num_paragraphs} segments...")
            video_segments, _ = split_video(video_path, num_paragraphs, dirs["video"])
            progress_detail.markdown(f"✅ Split complete ({num_paragraphs} segments)")

            step12_elapsed = time.time() - step_start
            progress_bar.progress(0.33)
            progress_detail.markdown(f"✅ TTS + Split complete ({step12_elapsed:.1f}s)")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # STEP 3: Speed-adjust each segment
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            step_status_placeholder.markdown(f"**Step 2/3:** Speed-adjusting {num_paragraphs} segments...")
            step_start = time.time()
            adjusted_segments = [None] * num_paragraphs
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(
                        speed_adjust_segment,
                        i, video_segments[i],
                        os.path.join(dirs["audio"], f"audio_{i}.mp3"),
                        dirs["adjusted"]
                    ): i for i in range(num_paragraphs)
                }
                for future in concurrent.futures.as_completed(futures):
                    idx = futures[future]
                    try:
                        adjusted_segments[idx] = future.result()
                    except Exception as e:
                        st.error(f"❌ Speed adjust failed for segment {idx+1}: {e}")
                    done = sum(1 for x in adjusted_segments if x is not None)
                    progress_bar.progress(0.33 + 0.33 * done / num_paragraphs)
                    progress_detail.markdown(f"⚡ Segment {done}/{num_paragraphs} speed adjusted")

            gc.collect()
            step3_elapsed = time.time() - step_start
            progress_detail.markdown(f"✅ All {num_paragraphs} segments speed-adjusted ({step3_elapsed:.1f}s)")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # FINAL STEP: Merge all speed-adjusted segments
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            step_status_placeholder.markdown("**Step 3/3:** Merging final video...")
            progress_detail.markdown("🔗 Merging segments...")
            step_start = time.time()
            output_video = os.path.join(dirs["temp"], "final_output.mp4")
            merge_speed_adjusted_segments(adjusted_segments, output_video)
            progress_bar.progress(1.0)
            final_merge_elapsed = time.time() - step_start
            progress_detail.markdown(f"✅ Final video merged ({final_merge_elapsed:.1f}s)")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # GENERATE SRT SUBTITLE FILE
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            progress_detail.markdown("📝 Generating SRT subtitles...")
            final_duration = get_video_duration(output_video)
            full_text = inputs["text"]
            sub_maker = SmartSubMaker(full_text, final_duration)
            srt_text = sub_maker.generate_subs()
            srt_path = os.path.join(dirs["temp"], "final_output.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_text)
            progress_detail.markdown("✅ SRT subtitles generated")

            gc.collect()
            
            st.session_state.processing_active = False
            st.session_state.output_video = output_video
            st.session_state.srt_path = srt_path
            st.session_state.dirs_path = dirs
            with open(output_video, "rb") as f:
                st.session_state.video_bytes = f.read()
            with open(srt_path, "rb") as f:
                st.session_state.srt_bytes = f.read()
            status.update(label="✅ Complete!", state="complete")
            st.write("✅ Processing complete. Download your video below.")

        except Exception as e:
            st.error(f"❌ Processing failed: {e}")
            st.session_state.processing_active = False
            return

        total_elapsed = time.time() - total_start
        timer_placeholder.markdown(f"⏱️ **Total: {format_time(total_elapsed)}**")
        step_status_placeholder.markdown("**✅ All steps complete!**")
        st.success(f"🎉 Completed in **{format_time(total_elapsed)}**")

    # Show download buttons even after rerun (outside the processing block)
    if st.session_state.get("output_video") and os.path.exists(st.session_state.get("output_video", "")):
        output_basename = st.session_state.get("output_basename", "BE_output")

        # Read bytes from session_state (stored once after processing)
        video_data = st.session_state.get("video_bytes")
        srt_data = st.session_state.get("srt_bytes")

        col_v, col_s = st.columns(2)
        with col_v:
            if video_data:
                st.download_button(
                    "📥 Download Video" if is_en else "📥 Download Video",
                    data=video_data,
                    file_name=f"{output_basename}.mp4",
                    mime="video/mp4"
                )
        with col_s:
            if srt_data:
                st.download_button(
                    "📝 Download SRT" if is_en else "📝 Download SRT",
                    data=srt_data,
                    file_name=f"{output_basename}.srt",
                    mime="text/plain"
                )

    st.markdown("---")
    label_reset = "🔄 Process Another Video" if is_en else "🔄 နောက်ထပ် ဗီဒီယို ထပ်လုပ်မယ်"
    if st.button(label_reset, use_container_width=True):
        if st.session_state.get("dirs_path"):
            shutil.rmtree(st.session_state.dirs_path["temp"], ignore_errors=True)
        if st.session_state.get("output_video") and os.path.exists(st.session_state.output_video):
            os.remove(st.session_state.output_video)
        st.session_state.processing_active = False
        st.session_state.output_video = None
        st.session_state.srt_path = None
        st.session_state.dirs_path = None
        st.session_state.video_bytes = None
        st.session_state.srt_bytes = None
        st.rerun()
if __name__ == "__main__":
    main()
