# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-06-23

### Added
- Initial release of Audiobook Creator
- Automatic audio file detection and sorting
- M4B audiobook creation with proper metadata
- Chapter indexing with multiple naming strategies:
  - TSV file mapping (highest priority)
  - Audio file metadata extraction
  - Filename-based naming (lowest priority)
- Adaptive bitrate calculation based on source codec efficiency
- BookPlayer compatibility with proper M4B formatting
- Cover art extraction and embedding from audio files
- Title selection options:
  - Manual override with `-t` flag
  - Interactive choice between metadata and directory name
- Multi-threaded AAC encoding support
- Quick mode for faster processing with lower bitrate
- Automatic temporary file management with crash-safe cleanup
- Cross-platform support (macOS, Linux, Windows)
- Comprehensive dependency checking with installation guides

### Features
- Support for multiple audio formats: MP3, M4A, WAV, FLAC, AAC, OGG, WMA
- Intelligent codec efficiency mapping for quality preservation
- Signal handling for graceful interruption and cleanup
- Proper audiobook metadata embedding (title, artist, genre, media_type)
- Chapter timing calculation with millisecond precision

### Dependencies
- Python 3.6+
- FFmpeg and FFprobe (external system dependencies)
- No additional Python packages required (uses only standard library)