# Streamlit Video & Text Processor with TTS

A powerful Streamlit application that combines text processing with video editing using Text-to-Speech (TTS) technology. This tool automatically synchronizes video segments with generated audio, applies custom visual effects, and creates a final merged video.

## Features

### 🎤 Voice & Audio Settings
- **14 Different Voices**: Choose from a variety of voice options with different genders and characteristics
- **Optional VoxCPM2 Voice Clone**: Upload a permitted 3–10 second reference clip and use the cloned voice for the video
- **Recap Styles**: Apply different vocal styles (Normal, Pitch variations, Speed combinations)
- **Emotions**: Select from 11 different emotional tones (Exciting, Calm, Professional, Narrative, Happy, Serious, Whisper, Sad, Sarcastic, Angry, Fear)
- **TTS Engine**: Uses `edge_tts` for high-quality audio generation

### 🎬 Video Editing Features
- **Custom Play Duration**: Adjust play duration from 1-5 seconds
- **Freeze Effects**: Create freeze frames with durations from 1-3 seconds each
- **Zoom Effects**: Apply Zoom In/Out effects during freeze moments for copyright protection
- **Automatic Synchronization**: Video speed automatically adjusts to match TTS audio duration

### 📊 Processing Capabilities
- **Paragraph-Based Splitting**: Automatically splits text into paragraphs
- **Video Segmentation**: Divides video into segments matching paragraph count
- **Parallel Processing**: Processes up to 5-10 segments simultaneously for faster execution
- **Automatic Merging**: Combines all processed segments into a single final video

## Installation

### Requirements
- Python 3.8+
- FFmpeg and FFprobe
- Streamlit
- edge_tts
- Other dependencies listed in `requirements.txt`

### Setup

1. Clone the repository:
```bash
git clone https://github.com/phyoethura99/streamlit-video-processor.git
cd streamlit-video-processor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Optional GPU voice cloning

The normal Edge-TTS mode works without a GPU. To enable the **Custom Voice Clone
(VoxCPM2)** panel, run the app on a CUDA GPU host with about 8 GB of VRAM and
install the optional dependencies:

```bash
pip install -r requirements-gpu.txt
```

Then open the **Custom Voice Clone (VoxCPM2)** panel, upload a 3–10 second
reference recording, enter the exact words spoken in that recording, and tick
the checkbox before starting video processing. The model is loaded lazily and
cached in memory. The app does not send the reference audio to a third-party
API; it runs the model on the machine hosting the app.

For the recommended low-memory setup, keep Streamlit on the 500 MB host and
run only `voice_clone_server.py` on a free Colab T4. The included
`colab_voxcpm_backend.ipynb` installs the GPU dependencies, starts the API, and
prints a temporary tunnel URL. Paste that URL and the notebook's token into the
Custom Voice Clone panel. A tablet can control the Streamlit app through the
browser; the tablet itself does not run the model.

The Colab runtime and tunnel URL are temporary and may disconnect. This is for
personal use and is not an always-on production API.

3. Ensure FFmpeg is installed:
```bash
# On Ubuntu/Debian
sudo apt-get install ffmpeg

# On macOS
brew install ffmpeg

# On Windows
# Download from https://ffmpeg.org/download.html
```

## Usage

Run the Streamlit application:
```bash
streamlit run app.py
```

For the remote backend setup, open `colab_voxcpm_backend.ipynb` in Colab,
select a T4 GPU, upload this repository as a ZIP, and run its cells in order.

The application will open in your browser at `http://localhost:8501`

### Step-by-Step Guide

1. **Configure Voice Settings**:
   - Select a voice from the dropdown (14 options available)
   - Choose a recap style (Normal, Pitch variations, Speed combinations)
   - Select an emotion to apply to the voice

2. **Configure Video Editing**:
   - Set play duration (1-5 seconds)
   - Set freeze 1 duration (1-3 seconds) and choose zoom effect
   - Set freeze 2 duration (1-3 seconds) and choose zoom effect

3. **Input Content**:
   - Enter your text in the text area (unlimited words)
   - Upload a video file (MP4, MOV, or AVI format, max 2GB, 1 hour duration)

4. **Process**:
   - Click the "Start Processing" button
   - Wait for processing to complete (progress bar shows status)
   - Download the final video

## How It Works

### Processing Pipeline

1. **Text Analysis**: Splits input text into paragraphs
2. **TTS Generation**: Generates audio for each paragraph using selected voice, style, and emotion
3. **Video Splitting**: Divides the input video into segments matching the number of paragraphs
4. **Speed Adjustment**: Adjusts video segment speed to match the duration of generated audio
5. **Effect Application**: Applies play/freeze/zoom cycles to each segment:
   - Play segment: Normal video playback for specified duration
   - Freeze 1: Freezes frame at play end with optional zoom effect
   - Freeze 2: Freezes frame at freeze1 end with optional zoom effect
6. **Parallel Processing**: Processes multiple segments simultaneously (5-10 workers)
7. **Merging**: Combines all processed segments into a single final video

### Example Cycle (Default Settings)
- **Play**: 3 seconds of normal video
- **Freeze 1**: 1 second freeze with optional zoom
- **Freeze 2**: 1 second freeze with optional zoom
- **Total Cycle**: 5 seconds

This cycle repeats throughout the entire video duration to match the audio length.

## Configuration

### Voice Options
The application includes 14 pre-configured voices with different characteristics for various use cases.

### Recap Styles
- Normal (0% speed, 0Hz pitch)
- ကျားကြီး ၁ (0% speed, 25Hz pitch)
- ကျားကြီး ၂ (0% speed, 35Hz pitch)
- ကျားကြီး ၃ (0% speed, 45Hz pitch)
- နီလာ ချွဲသံ (0% speed, 40Hz pitch)
- ပေါင်းစပ် ၁၅ (15% speed, 15Hz pitch)
- ပေါင်းစပ် ၃၀ (30% speed, 30Hz pitch)
- ပေါင်းစပ် ၅၀ (50% speed, 50Hz pitch)
- အသံသေး ၂၀ (0% speed, 20Hz pitch)
- အသံသေး ၅၀ (0% speed, 50Hz pitch)

### Emotions
Each emotion applies specific speed and pitch adjustments for different tones and moods.

## Limitations

- **Video Format**: Currently supports MP4, MOV, and AVI formats
- **File Size**: Maximum 2GB per video
- **Duration**: Maximum 1 hour per video
- **Text**: Paragraphs are separated by double newlines
- **Processing Time**: Depends on video length, text length, and system resources
- **Audio Quality**: Limited by edge_tts service availability

## Troubleshooting

### FFmpeg Not Found
Ensure FFmpeg is installed and added to your system PATH:
```bash
ffmpeg -version
ffprobe -version
```

### Memory Issues
If processing large videos:
- Reduce the number of parallel workers in the code (change `max_workers` value)
- Process shorter videos or text segments
- Ensure sufficient disk space for temporary files

### Audio Quality Issues
- Try different recap styles and emotions
- Ensure text is properly formatted with clear paragraph breaks
- Check that edge_tts service is accessible

## Project Structure

```
streamlit-video-processor/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .gitignore            # Git ignore rules
└── temp_processing/      # Temporary files (auto-created)
    ├── audio/            # Generated audio files
    ├── video/            # Video segments
    └── final_segments/   # Processed video segments
```

## Dependencies

- **streamlit**: Web application framework
- **edge_tts**: Text-to-speech engine
- **ffmpeg**: Video processing
- **ffprobe**: Media information tool
- **asyncio**: Asynchronous I/O for TTS
- **concurrent.futures**: Parallel processing

## Performance Notes

- Processing time depends on:
  - Video length
  - Number of paragraphs
  - System CPU and disk speed
  - Number of parallel workers (default: 5)

- Typical processing times:
  - 5-minute video with 10 paragraphs: 2-5 minutes
  - 10-minute video with 20 paragraphs: 5-15 minutes
  - 30-minute video with 50 paragraphs: 15-45 minutes

## Future Enhancements

- [ ] Support for more video formats (WebM, MOV, etc.)
- [ ] Custom voice creation
- [x] VoxCPM2 custom voice cloning on an optional CUDA host
- [ ] Real-time preview
- [ ] Batch processing
- [ ] Cloud storage integration
- [ ] Advanced audio effects
- [ ] Subtitle generation
- [ ] Multi-language support

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

## Disclaimer

This tool is provided as-is for educational and personal use. Users are responsible for ensuring they have the right to use any videos or audio content processed with this application.
