# Audiobook Creator

A command-line tool that combines audio files into a properly formatted M4B audiobook with chapter indexing, cover art, and BookPlayer compatibility.

## Features

- **Smart Chapter Naming**: Uses TSV file > metadata > filename (priority order)
- **Adaptive Bitrate**: Automatically adjusts output quality based on source codec efficiency
- **Cover Art Extraction**: Automatically extracts and embeds cover art from audio files
- **BookPlayer Compatible**: Creates proper M4B format with embedded metadata
- **Flexible Title Selection**: Override title or choose between metadata and directory name
- **Multi-threaded Processing**: Utilizes all CPU cores for faster encoding
- **Automatic Cleanup**: Safely handles temporary files with crash protection

## Installation

### From PyPI (Recommended)
```bash
pip install audiobook-creator
```

### From Source
```bash
git clone https://github.com/Paying4464/audiobook-creator.git
cd audiobook-creator
```

## Requirements

- Python 3.6+
- FFmpeg and FFprobe

### Installing FFmpeg

**macOS:**
```bash
# Using Homebrew
brew install ffmpeg

# Using MacPorts
sudo port install ffmpeg
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# CentOS/RHEL/Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Using Scoop
scoop install ffmpeg
```

## Usage

### Basic Usage
```bash
# If installed via pip:
audiobook-creator -i /path/to/audio/files -o output.m4b

# If running from source:
./main.py -i /path/to/audio/files -o output.m4b
```

### All Options
```bash
audiobook-creator -i INPUT_DIR -o OUTPUT_FILE [OPTIONS]
```

### Options

- `-i, --input` : Source directory containing audio files (required)
- `-o, --output` : Output M4B file path (required)
- `-I, --index` : TSV file with filename and chapter name mapping
- `-t, --title` : Override audiobook title
- `--quick` : Use lower bitrate (16k) for faster processing

### Examples

**Basic conversion:**
```bash
audiobook-creator -i "./My Audiobook Files" -o "My Audiobook.m4b"
```

**With custom title:**
```bash
audiobook-creator -i "./Audio Files" -o "Book.m4b" -t "My Custom Title"
```

**With chapter index file:**
```bash
audiobook-creator -i "./Audio Files" -o "Book.m4b" -I chapters.tsv
```

**Quick mode (faster, lower quality):**
```bash
audiobook-creator -i "./Audio Files" -o "Book.m4b" --quick
```

## Chapter Index File Format

Create a TSV (tab-separated values) file with filename and chapter name:

```
01-intro.mp3	Introduction
02-chapter1.mp3	The Mind-Body Connection
03-chapter2.mp3	When the Body Says No
04-conclusion.mp3	Conclusion
```

## Supported Audio Formats

- MP3 (.mp3)
- M4A (.m4a)
- WAV (.wav)
- FLAC (.flac)
- AAC (.aac)
- OGG (.ogg)
- WMA (.wma)

## How It Works

1. **File Discovery**: Scans input directory for audio files
2. **Metadata Extraction**: Reads metadata from first file for book info
3. **Title Selection**: Uses -t flag, or prompts for metadata vs directory name
4. **Bitrate Analysis**: Analyzes source files to determine optimal AAC bitrate
5. **Chapter Creation**: Creates chapters using priority: TSV file > metadata > filename
6. **Cover Art**: Extracts cover art from audio files if available
7. **M4B Creation**: Combines everything into BookPlayer-compatible M4B file

## Codec Efficiency

The tool automatically adjusts output bitrate based on source codec efficiency:

- **MP3**: Needs ~25% more bitrate than AAC for same quality
- **AAC/M4A**: Baseline (1:1 ratio)
- **Vorbis/OGG**: ~10% more efficient than AAC
- **Opus**: ~30% more efficient than AAC
- **FLAC/WAV**: Uses original bitrate as reference
- **WMA**: Similar efficiency to AAC

## Troubleshooting

**"No audio files found"**
- Check that your input directory contains supported audio file formats
- Ensure file extensions are recognized (.mp3, .m4a, etc.)

**"Missing required dependencies"**
- Install FFmpeg using the instructions above
- Restart your terminal after installation

**BookPlayer doesn't recognize file**
- Ensure the output file has .m4b extension
- Check that the file size is reasonable (not 0 bytes)
- Try transferring the file again to your device

**Slow processing**
- Use `--quick` flag for faster encoding with lower quality
- Note that AAC encoding is inherently single-threaded

## License

This project is open source. Feel free to modify and distribute.