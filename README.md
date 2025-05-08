# Audio Transcription Tool 🎙️

A sleek, cross-platform tool for transcribing audio files into text with automatic OS detection and dependency setup.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-yellow.svg)](https://www.python.org/)

## ✨ Features

- **Cross-Platform**: Works seamlessly on Windows, macOS, and Linux with automatic OS detection.
- **Auto Dependency Setup**: Installs required dependencies based on your system.
- **Flexible Audio Support**: Transcribes WAV, MP3, and other formats using FFmpeg.
- **Smart Chunking**: Splits long audio files into manageable pieces for accurate transcription.
- **Google Speech API**: Leverages Google's speech recognition for high-quality results.
- **User-Friendly CLI**: Simple commands with clear feedback.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/audio-transcriber.git
cd audio-transcriber

# Install dependencies automatically
python audio_transcriber.py --install-deps
```

<button onclick="navigator.clipboard.writeText('git clone https://github.com/yourusername/audio-transcriber.git\ncd audio-transcriber\npython audio_transcriber.py --install-deps')">Copy</button>

### Basic Usage

```bash
# Transcribe an audio file
python audio_transcriber.py path/to/audio_file.mp3
```

<button onclick="navigator.clipboard.writeText('python audio_transcriber.py path/to/audio_file.mp3')">Copy</button>

The transcription will be saved as `audio_file_transcription.txt` in the same directory.

### Specify Output File

```bash
# Save transcription to a custom location
python audio_transcriber.py path/to/audio_file.mp3 -o path/to/output.txt
```

<button onclick="navigator.clipboard.writeText('python audio_transcriber.py path/to/audio_file.mp3 -o path/to/output.txt')">Copy</button>

## 🔧 Dependencies

The script automatically installs:

- **Python Packages**: `SpeechRecognition`, `pydub`
- **FFmpeg**: For processing non-WAV audio formats

### Manual Installation (if needed)

If automatic installation fails, install dependencies manually:

```bash
# Python packages
pip install SpeechRecognition pydub
```

<button onclick="navigator.clipboard.writeText('pip install SpeechRecognition pydub')">Copy</button>

```bash
# FFmpeg (Ubuntu/Debian)
sudo apt update && sudo apt install -y ffmpeg
```

<button onclick="navigator.clipboard.writeText('sudo apt update && sudo apt install -y ffmpeg')">Copy</button>

```bash
# FFmpeg (macOS with Homebrew)
brew install ffmpeg
```

<button onclick="navigator.clipboard.writeText('brew install ffmpeg')">Copy</button>

**Windows**: Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html) and add it to your PATH.

## 🧩 How It Works

1. **OS Detection**: Identifies your operating system to tailor dependency installation.
2. **Audio Processing**: Converts non-WAV files to WAV format using FFmpeg.
3. **Smart Chunking**: Splits audio based on silence for efficient processing.
4. **Speech Recognition**: Uses Google's API to transcribe each chunk.
5. **Output**: Combines transcriptions into a single text file.

## ⚠️ Troubleshooting

- **FFmpeg Errors**: Ensure FFmpeg is installed and added to your PATH.
- **Audio Quality**: Record in a quiet environment for better accuracy.
- **Large Files**: Very long audio files may require additional processing time.

## 📄 License

This project is licensed under the [MIT License](LICENSE) — feel free to use, modify, and distribute!

## 🌟 Contributing

Contributions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/yourusername/audio-transcriber).