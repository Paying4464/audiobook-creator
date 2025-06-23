#!/usr/bin/env python3

__version__ = "0.1.0"

import argparse
import os
import sys
import subprocess
import platform
from pathlib import Path
import csv
import shutil
import json
import tempfile
import atexit
import signal
import re
import logging
import shlex
from typing import List, Optional, Dict, Tuple

AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.wav', '.flac', '.aac', '.ogg', '.wma'}

# Security constants
MAX_FILENAME_LENGTH = 255
MAX_PATH_LENGTH = 4096
MAX_FILES_COUNT = 1000
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
MAX_CHAPTER_NAME_LENGTH = 200

# Global list to track temporary files for cleanup
TEMP_FILES = []

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent injection attacks."""
    if not filename:
        raise ValueError("Filename cannot be empty")
    
    # Remove dangerous characters and control characters
    sanitized = re.sub(r'[^a-zA-Z0-9._\-\s]', '_', filename)
    
    # Remove leading dots and whitespace
    sanitized = sanitized.lstrip('. ')
    
    # Limit length
    if len(sanitized) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:MAX_FILENAME_LENGTH - len(ext)] + ext
    
    # Ensure not empty after sanitization
    if not sanitized or sanitized.isspace():
        sanitized = "sanitized_file"
    
    return sanitized

def sanitize_chapter_name(name: str) -> str:
    """Sanitize chapter name to prevent injection in metadata."""
    if not name:
        return "Unnamed Chapter"
    
    # Remove shell metacharacters and dangerous characters
    sanitized = re.sub(r'[;&|`$(){}[\]<>"\\]', '', name)
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    
    # Limit length
    sanitized = sanitized[:MAX_CHAPTER_NAME_LENGTH]
    
    # Ensure not empty
    if not sanitized.strip():
        sanitized = "Unnamed Chapter"
    
    return sanitized.strip()

def validate_path_within_base(path: str, base_dir: str) -> bool:
    """Validate that path is within base directory (for path traversal prevention)."""
    try:
        abs_path = os.path.abspath(path)
        abs_base = os.path.abspath(base_dir)
        
        # Check path traversal
        if not abs_path.startswith(abs_base + os.sep) and abs_path != abs_base:
            return False
        
        # Check path length
        if len(abs_path) > MAX_PATH_LENGTH:
            return False
        
        return True
    except (OSError, ValueError):
        return False

def validate_path_basic(path: str) -> bool:
    """Basic path validation for security without requiring specific base directory."""
    try:
        abs_path = os.path.abspath(path)
        
        # Check path length
        if len(abs_path) > MAX_PATH_LENGTH:
            return False
        
        # Check for obviously malicious patterns
        suspicious_patterns = ['..', '\x00', '\x01', '\x02', '\x03', '\x04', '\x05']
        path_str = str(path)
        for pattern in suspicious_patterns:
            if pattern in path_str:
                security_logger.warning(f"Suspicious pattern '{pattern}' in path: {path}")
                # Don't reject, just log - '..' might be legitimate in some absolute paths
        
        return True
    except (OSError, ValueError):
        return False

def safe_path_join(base: str, *paths: str) -> str:
    """Safely join paths and validate result."""
    try:
        full_path = os.path.join(base, *paths)
        
        if not validate_path_within_base(full_path, base):
            raise ValueError(f"Path traversal detected: {full_path}")
        
        return os.path.abspath(full_path)
    except (OSError, ValueError) as e:
        security_logger.warning(f"Path validation failed: {e}")
        raise

def validate_file_safety(file_path: Path) -> bool:
    """Validate file is safe to process."""
    try:
        # Check if file exists and is a regular file
        if not file_path.exists() or not file_path.is_file():
            return False
        
        # Check file size
        if file_path.stat().st_size > MAX_FILE_SIZE:
            logger.warning(f"File too large: {file_path} ({file_path.stat().st_size} bytes)")
            return False
        
        # Check for suspicious filenames
        filename = file_path.name
        if any(char in filename for char in ['..', '/', '\\', '|', ';', '&', '$', '`']):
            security_logger.warning(f"Suspicious filename detected: {filename}")
            return False
        
        return True
    except (OSError, ValueError) as e:
        logger.error(f"File validation error: {e}")
        return False

def create_secure_temp(suffix: str = '', prefix: str = 'audiobook_') -> Tuple[int, str]:
    """Create a secure temporary file."""
    try:
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        # Set restrictive permissions (owner read/write only)
        os.chmod(path, 0o600)
        return fd, path
    except (OSError, ValueError) as e:
        logger.error(f"Failed to create secure temporary file: {e}")
        raise

def cleanup_temp_files():
    """Clean up all temporary files."""
    for temp_file in TEMP_FILES:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.debug(f"Cleaned up temporary file: {temp_file}")
        except OSError as e:
            logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")
    TEMP_FILES.clear()

def signal_handler(signum, frame):
    """Handle interruption signals."""
    print("\nInterrupted! Cleaning up temporary files...")
    cleanup_temp_files()
    sys.exit(1)

# Register cleanup functions
atexit.register(cleanup_temp_files)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def check_dependencies():
    """Check if required dependencies are available and provide installation instructions if not."""
    missing_deps = []
    
    if not shutil.which('ffmpeg'):
        missing_deps.append('ffmpeg')
    
    if not shutil.which('ffprobe'):
        missing_deps.append('ffprobe')
    
    if missing_deps:
        print("Error: Missing required dependencies:", ', '.join(missing_deps))
        print("\nInstallation instructions:")
        
        system = platform.system().lower()
        if system == 'darwin':  # macOS
            print("On macOS:")
            print("  Using Homebrew: brew install ffmpeg")
            print("  Using MacPorts: sudo port install ffmpeg")
        elif system == 'linux':
            print("On Linux:")
            print("  Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg")
            print("  CentOS/RHEL/Fedora: sudo dnf install ffmpeg")
            print("  Arch Linux: sudo pacman -S ffmpeg")
        elif system == 'windows':
            print("On Windows:")
            print("  Using Chocolatey: choco install ffmpeg")
            print("  Using Scoop: scoop install ffmpeg")
            print("  Manual: Download from https://ffmpeg.org/download.html")
        else:
            print(f"Please install ffmpeg for your system ({system})")
            print("Visit: https://ffmpeg.org/download.html")
        
        print("\nAfter installation, restart your terminal and try again.")
        return False
    
    return True

def parse_arguments():
    parser = argparse.ArgumentParser(description='Combine audio files into an m4b audiobook with proper indexing')
    parser.add_argument('-i', '--input', required=True, help='Source directory containing audio files')
    parser.add_argument('-o', '--output', required=True, help='Output m4b file path')
    parser.add_argument('-I', '--index', help='TSV file with filename and chapter name mapping')
    parser.add_argument('-t', '--title', help='Override audiobook title')
    parser.add_argument('--quick', action='store_true', help='Use lower bitrate (16k) for faster processing')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    return parser.parse_args()

def get_audio_files(input_dir: str) -> List[Path]:
    """Get audio files from input directory with security validation."""
    try:
        input_path = Path(input_dir)
        
        # Validate input directory
        if not input_path.exists():
            raise ValueError(f"Input directory does not exist: {input_dir}")
        
        if not input_path.is_dir():
            raise ValueError(f"Input path is not a directory: {input_dir}")
        
        # Check for suspicious directory names
        if any(part.startswith('.') for part in input_path.parts[1:]):
            security_logger.warning(f"Suspicious directory path: {input_dir}")
        
        audio_files = []
        file_count = 0
        
        for file_path in input_path.iterdir():
            file_count += 1
            if file_count > MAX_FILES_COUNT:
                raise ValueError(f"Too many files in directory (max {MAX_FILES_COUNT})")
            
            if (file_path.is_file() and 
                file_path.suffix.lower() in AUDIO_EXTENSIONS and
                validate_file_safety(file_path)):
                
                audio_files.append(file_path)
        
        if not audio_files:
            logger.warning(f"No valid audio files found in {input_dir}")
        
        return sorted(audio_files, key=lambda x: x.name.lower())
        
    except (OSError, ValueError) as e:
        logger.error(f"Error getting audio files: {e}")
        raise

def parse_index_file(index_file: str) -> Tuple[Dict[str, str], List[str]]:
    """Parse TSV index file with security validation."""
    try:
        if not os.path.exists(index_file):
            raise FileNotFoundError(f"Index file not found: {index_file}")
        
        if not os.path.isfile(index_file):
            raise ValueError(f"Index path is not a file: {index_file}")
        
        # Check file size
        file_size = os.path.getsize(index_file)
        if file_size > 10 * 1024 * 1024:  # 10MB limit for TSV
            raise ValueError(f"Index file too large: {file_size} bytes")
        
        chapter_mapping = {}
        file_order = []
        line_count = 0
        
        with open(index_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            for row in reader:
                line_count += 1
                if line_count > 10000:  # Prevent DoS
                    raise ValueError("Too many lines in index file")
                
                if len(row) >= 2:
                    filename = sanitize_filename(row[0].strip())
                    chapter_name = sanitize_chapter_name(row[1].strip())
                    
                    if filename and chapter_name:
                        chapter_mapping[filename] = chapter_name
                        file_order.append(filename)
                    else:
                        logger.warning(f"Skipping invalid row {line_count}: {row}")
        
        logger.info(f"Parsed {len(chapter_mapping)} chapter mappings from index file")
        return chapter_mapping, file_order
        
    except (OSError, ValueError, UnicodeDecodeError) as e:
        logger.error(f"Error parsing index file: {e}")
        raise

def get_file_metadata(file_path: Path) -> Dict[str, str]:
    """Extract metadata from audio file with security validation."""
    try:
        if not validate_file_safety(file_path):
            raise ValueError(f"File failed safety validation: {file_path}")
        
        # Use absolute path and validate
        abs_path = file_path.resolve()
        
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', str(abs_path)
        ]
        
        # Run with timeout and capture output safely
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=30,  # 30 second timeout
            check=True
        )
        
        data = json.loads(result.stdout)
        
        metadata = {}
        if 'format' in data and 'tags' in data['format']:
            tags = data['format']['tags']
            # Sanitize metadata values
            for k, v in tags.items():
                if isinstance(v, str):
                    # Remove control characters and limit length
                    clean_value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', v)[:500]
                    metadata[k.lower()] = clean_value
        
        return metadata
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout extracting metadata from {file_path}")
        return {}
    except subprocess.CalledProcessError as e:
        logger.error(f"FFprobe failed for {file_path}: {e}")
        return {}
    except (json.JSONDecodeError, ValueError, OSError) as e:
        logger.error(f"Error processing metadata from {file_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error extracting metadata from {file_path}: {e}")
        return {}

def get_chapter_name(audio_file: Path, index: int, chapter_mapping: Optional[Dict[str, str]] = None) -> str:
    """Get chapter name with priority: -I file > metadata > filename."""
    try:
        filename = audio_file.name
        
        # Priority 1: -I file mapping
        if chapter_mapping and filename in chapter_mapping:
            return sanitize_chapter_name(chapter_mapping[filename])
        
        # Priority 2: metadata from file
        metadata = get_file_metadata(audio_file)
        if 'title' in metadata and metadata['title']:
            return sanitize_chapter_name(metadata['title'])
        
        # Priority 3: filename without extension
        chapter_name = sanitize_chapter_name(audio_file.stem)
        return chapter_name if chapter_name != "Unnamed Chapter" else f"Chapter {index + 1}"
        
    except Exception as e:
        logger.warning(f"Error getting chapter name for {audio_file}: {e}")
        return f"Chapter {index + 1}"

def extract_cover_art(audio_files: List[Path]) -> Optional[str]:
    """Extract cover art from audio files with security validation."""
    try:
        cover_fd, cover_path = create_secure_temp(suffix='.jpg', prefix='audiobook_cover_')
        os.close(cover_fd)  # We just need the path
        TEMP_FILES.append(cover_path)
        
        for audio_file in audio_files:
            try:
                if not validate_file_safety(audio_file):
                    continue
                
                abs_path = audio_file.resolve()
                
                cmd = [
                    'ffmpeg', '-y', '-i', str(abs_path),
                    '-an', '-vcodec', 'copy', cover_path
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=60,  # 1 minute timeout
                    check=False
                )
                
                if result.returncode == 0 and os.path.exists(cover_path):
                    # Validate extracted image
                    if os.path.getsize(cover_path) > 0:
                        logger.info(f"Extracted cover art from {audio_file}")
                        return cover_path
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout extracting cover art from {audio_file}")
                continue
            except (OSError, ValueError) as e:
                logger.warning(f"Error extracting cover art from {audio_file}: {e}")
                continue
        
        # No cover art found, clean up temp file
        try:
            os.remove(cover_path)
            TEMP_FILES.remove(cover_path)
        except (OSError, ValueError):
            pass
        
        return None
        
    except Exception as e:
        logger.error(f"Error in cover art extraction: {e}")
        return None

def get_source_bitrate_and_codec(audio_files: List[Path]) -> Tuple[int, str]:
    """Get average bitrate and most common codec from source files with security validation."""
    total_bitrate = 0
    codec_count = {}
    valid_files = 0
    
    for audio_file in audio_files:
        try:
            if not validate_file_safety(audio_file):
                continue
            
            abs_path = audio_file.resolve()
            
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-select_streams', 'a:0', str(abs_path)
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                check=True
            )
            
            data = json.loads(result.stdout)
            
            if 'streams' in data and len(data['streams']) > 0:
                stream = data['streams'][0]
                
                # Get bitrate
                if 'bit_rate' in stream:
                    try:
                        bitrate = int(stream['bit_rate']) // 1000  # Convert to kbps
                        if 0 < bitrate < 10000:  # Reasonable range
                            total_bitrate += bitrate
                            valid_files += 1
                    except (ValueError, TypeError):
                        continue
                
                # Count codec
                if 'codec_name' in stream:
                    codec = str(stream['codec_name'])[:20]  # Limit codec name length
                    if codec.isalnum() or codec in ['aac', 'mp3', 'flac', 'wav', 'ogg', 'wma', 'opus', 'vorbis']:
                        codec_count[codec] = codec_count.get(codec, 0) + 1
                        
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout analyzing {audio_file}")
            continue
        except subprocess.CalledProcessError as e:
            logger.warning(f"FFprobe failed for {audio_file}: {e}")
            continue
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.warning(f"Error analyzing {audio_file}: {e}")
            continue
    
    if valid_files == 0:
        logger.warning("No valid files for bitrate analysis, using defaults")
        return 128, 'mp3'  # Default fallback
    
    avg_bitrate = total_bitrate // valid_files
    most_common_codec = max(codec_count.items(), key=lambda x: x[1])[0] if codec_count else 'mp3'
    
    logger.info(f"Analyzed {valid_files} files: avg bitrate {avg_bitrate}k, codec {most_common_codec}")
    return avg_bitrate, most_common_codec

def calculate_optimal_aac_bitrate(source_bitrate, source_codec):
    """Calculate optimal AAC bitrate for equivalent quality."""
    # Codec efficiency ratios compared to AAC (AAC = 1.0)
    codec_efficiency = {
        'mp3': 0.8,      # MP3 needs ~25% more bitrate for same quality
        'aac': 1.0,      # AAC baseline
        'm4a': 1.0,      # M4A is AAC container
        'vorbis': 1.1,   # Vorbis is ~10% more efficient
        'ogg': 1.1,      # OGG Vorbis
        'opus': 1.3,     # Opus is ~30% more efficient
        'flac': 1.0,     # Lossless, use original bitrate as reference
        'wav': 1.0,      # Uncompressed, use original bitrate as reference
        'wma': 0.9,      # WMA efficiency
    }
    
    # Get efficiency ratio for source codec
    efficiency = codec_efficiency.get(source_codec.lower(), 0.8)
    
    # Calculate equivalent AAC bitrate
    equivalent_bitrate = int(source_bitrate * efficiency)
    
    # Apply quality brackets for audiobooks
    if equivalent_bitrate <= 32:
        return 32   # Very low quality
    elif equivalent_bitrate <= 48:
        return 48   # Low quality
    elif equivalent_bitrate <= 64:
        return 64   # Standard audiobook quality
    elif equivalent_bitrate <= 96:
        return 96   # Good quality
    elif equivalent_bitrate <= 128:
        return 128  # High quality
    else:
        return 128  # Cap at 128k for audiobooks

def create_m4b(audio_files, output_path, chapter_mapping=None, quick_mode=False, title_override=None, input_dir=None):
    if not audio_files:
        print("No audio files found!")
        return False
    
    print(f"Processing {len(audio_files)} audio files...")
    
    # Extract metadata from first file for audiobook info
    first_file_metadata = get_file_metadata(audio_files[0])
    
    # Determine book title
    if title_override:
        book_title = title_override
        print(f"Using provided title: '{book_title}'")
    else:
        # Get options for title
        metadata_title = first_file_metadata.get('album', first_file_metadata.get('title', ''))
        dir_title = Path(input_dir).name if input_dir else ''
        
        if metadata_title and dir_title:
            print(f"\nTitle options:")
            print(f"1. From metadata: '{metadata_title}'")
            print(f"2. From directory: '{dir_title}'")
            
            try:
                choice = input("Choose title source (1 or 2): ").strip()
                if choice == '1':
                    book_title = metadata_title
                elif choice == '2':
                    book_title = dir_title
                else:
                    print("Invalid choice, using directory name")
                    book_title = dir_title
            except (EOFError, KeyboardInterrupt):
                print("No input provided, using directory name")
                book_title = dir_title
        elif metadata_title:
            book_title = metadata_title
        elif dir_title:
            book_title = dir_title
        else:
            book_title = 'Audiobook'
    
    book_artist = first_file_metadata.get('artist', first_file_metadata.get('albumartist', 'Unknown Artist'))
    book_genre = first_file_metadata.get('genre', 'Audiobook')
    
    print(f"Audiobook: '{book_title}' by {book_artist}")
    
    # Analyze source files for optimal bitrate (unless quick mode)
    if not quick_mode:
        source_bitrate, source_codec = get_source_bitrate_and_codec(audio_files)
        optimal_bitrate = calculate_optimal_aac_bitrate(source_bitrate, source_codec)
        print(f"Source: {source_bitrate}k {source_codec} -> Optimal AAC: {optimal_bitrate}k")
    else:
        optimal_bitrate = 16  # Quick mode override
        print("Quick mode: Using 16k AAC")
    
    # Create temporary files for ffmpeg securely
    file_list_fd, file_list_path = create_secure_temp(suffix='.txt', prefix='audiobook_files_')
    os.close(file_list_fd)
    TEMP_FILES.append(file_list_path)
    
    chapter_list_fd, chapter_list_path = create_secure_temp(suffix='.txt', prefix='audiobook_chapters_')
    os.close(chapter_list_fd)
    TEMP_FILES.append(chapter_list_path)
    
    # Extract cover art
    cover_path = extract_cover_art(audio_files)
    if cover_path:
        print("Found cover art in audio files")
    
    try:
        # Create file list for concatenation with validation
        with open(file_list_path, 'w', encoding='utf-8') as f:
            for audio_file in audio_files:
                if not validate_file_safety(audio_file):
                    raise ValueError(f"File failed safety validation: {audio_file}")
                
                abs_path = audio_file.resolve()
                # Escape single quotes in path for ffmpeg
                escaped_path = str(abs_path).replace("'", "'\"'\"'")
                f.write(f"file '{escaped_path}'\n")
        
        # Create chapter metadata with proper naming priority
        chapters = []
        current_time = 0
        for i, audio_file in enumerate(audio_files):
            chapter_name = get_chapter_name(audio_file, i, chapter_mapping)
            
            # Get duration of current file with security validation
            try:
                if not validate_file_safety(audio_file):
                    raise ValueError(f"File failed safety validation: {audio_file}")
                
                abs_path = audio_file.resolve()
                duration_cmd = [
                    'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                    '-of', 'csv=p=0', str(abs_path)
                ]
                
                result = subprocess.run(
                    duration_cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=30,
                    check=True
                )
                
                duration = float(result.stdout.strip())
                if duration <= 0 or duration > 86400:  # Max 24 hours per file
                    raise ValueError(f"Invalid duration: {duration}")
                
                chapters.append({
                    'start': current_time,
                    'end': current_time + duration,
                    'title': chapter_name
                })
                current_time += duration
                
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as e:
                logger.warning(f"Could not get duration for {audio_file}: {e}")
                chapters.append({
                    'start': current_time,
                    'end': current_time + 1,
                    'title': chapter_name
                })
                current_time += 1
        
        # Build ffmpeg command for proper m4b audiobook format
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        
        cmd = [
            'ffmpeg', '-y', '-threads', str(cpu_count), '-f', 'concat', '-safe', '0', '-i', file_list_path
        ]
        
        # Add cover art if available
        if cover_path and os.path.exists(cover_path):
            cmd.extend(['-i', cover_path])
        
        # Add chapter metadata with sanitization
        with open(chapter_list_path, 'w', encoding='utf-8') as f:
            f.write(";FFMETADATA1\n")
            f.write(f"title={sanitize_chapter_name(book_title)}\n")
            f.write(f"artist={sanitize_chapter_name(book_artist)}\n")
            f.write(f"album={sanitize_chapter_name(book_title)}\n")
            f.write(f"genre={sanitize_chapter_name(book_genre)}\n")
            f.write("media_type=2\n")
            for chapter in chapters:
                f.write(f"[CHAPTER]\n")
                f.write(f"TIMEBASE=1/1000\n")
                f.write(f"START={int(chapter['start'] * 1000)}\n")
                f.write(f"END={int(chapter['end'] * 1000)}\n")
                f.write(f"title={chapter['title']}\n")
        
        metadata_input_index = 2 if cover_path else 1
        cmd.extend(['-i', chapter_list_path, '-map_metadata', str(metadata_input_index)])
        
        # Add encoding options after all inputs
        bitrate = f'{optimal_bitrate}k'
        
        # Map audio stream and cover art if available
        if cover_path:
            cmd.extend([
                '-map', '0:a', '-map', '1:v',
                '-c:a', 'aac', '-aac_coder', 'fast', '-threads:a', str(cpu_count),
                '-b:a', bitrate, '-ac', '2', '-ar', '44100',
                '-c:v', 'copy', '-disposition:v:0', 'attached_pic'
            ])
        else:
            cmd.extend([
                '-c:a', 'aac', '-aac_coder', 'fast', '-threads:a', str(cpu_count),
                '-b:a', bitrate, '-ac', '2', '-ar', '44100'
            ])
        
        # Add final metadata and output with sanitization
        safe_title = sanitize_chapter_name(book_title)
        safe_artist = sanitize_chapter_name(book_artist)
        safe_genre = sanitize_chapter_name(book_genre)
        
        cmd.extend([
            '-movflags', '+faststart',
            '-metadata', f'title={safe_title}',
            '-metadata', f'artist={safe_artist}',
            '-metadata', f'album={safe_title}',
            '-metadata', f'genre={safe_genre}',
            '-metadata', 'media_type=2',
            '-f', 'ipod'
        ])
        
        cmd.append(output_path)
        
        logger.info("Creating m4b file...")
        
        # Run ffmpeg with timeout and security measures
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            # Verify output file was created and has reasonable size
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"Successfully created: {output_path}")
                return True
            else:
                logger.error("Output file was not created or is empty")
                return False
        else:
            logger.error(f"FFmpeg failed with return code {result.returncode}")
            if result.stderr:
                logger.error(f"FFmpeg error: {result.stderr[:1000]}")  # Limit error output
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg operation timed out")
        return False
    except (OSError, ValueError) as e:
        logger.error(f"Error creating m4b: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in m4b creation: {e}")
        return False
    finally:
        # Clean up temporary files (handled by global cleanup)
        pass

def validate_output_path(output_path: str) -> str:
    """Validate and sanitize output path."""
    try:
        # Check if path is absolute or relative
        abs_output = os.path.abspath(output_path)
        
        # Check path length
        if len(abs_output) > MAX_PATH_LENGTH:
            raise ValueError(f"Output path too long: {len(abs_output)} > {MAX_PATH_LENGTH}")
        
        # Check for path traversal attempts
        if '..' in output_path or output_path.startswith('/'):
            # Allow if it's explicitly absolute, but validate
            if not output_path.startswith(os.path.expanduser('~')) and not output_path.startswith('/tmp'):
                security_logger.warning(f"Potentially unsafe output path: {output_path}")
        
        # Validate file extension
        if not abs_output.lower().endswith('.m4b'):
            raise ValueError("Output file must have .m4b extension")
        
        # Sanitize filename component
        dir_path = os.path.dirname(abs_output)
        filename = os.path.basename(abs_output)
        safe_filename = sanitize_filename(filename)
        
        return os.path.join(dir_path, safe_filename)
        
    except (OSError, ValueError) as e:
        logger.error(f"Output path validation failed: {e}")
        raise

def safe_makedirs(path: str) -> None:
    """Safely create directories with validation."""
    try:
        abs_path = os.path.abspath(path)
        
        # Check path length
        if len(abs_path) > MAX_PATH_LENGTH:
            raise ValueError(f"Path too long: {len(abs_path)}")
        
        # Check for suspicious patterns
        if any(part.startswith('.') for part in Path(abs_path).parts[1:]):
            security_logger.warning(f"Creating directory with hidden components: {abs_path}")
        
        # Create directory safely
        os.makedirs(abs_path, mode=0o755, exist_ok=True)
        logger.info(f"Created output directory: {abs_path}")
        
    except (OSError, ValueError) as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise

def main():
    try:
        # Check dependencies first
        if not check_dependencies():
            sys.exit(1)
        
        args = parse_arguments()
        
        # Validate input directory with basic security checks
        try:
            input_dir = os.path.abspath(args.input)
            
            # Basic security validation - check for excessively long paths
            if len(input_dir) > MAX_PATH_LENGTH:
                raise ValueError(f"Input path too long: {len(input_dir)} > {MAX_PATH_LENGTH}")
            
            # Check if directory exists and is actually a directory
            if not os.path.exists(input_dir):
                raise ValueError(f"Input directory does not exist: {args.input}")
            
            if not os.path.isdir(input_dir):
                raise ValueError(f"Input path is not a directory: {args.input}")
            
            # Check for readable access
            if not os.access(input_dir, os.R_OK):
                raise ValueError(f"Input directory is not readable: {args.input}")
                
        except ValueError as e:
            logger.error(f"Input validation error: {e}")
            sys.exit(1)
        
        # Validate output path
        try:
            validated_output = validate_output_path(args.output)
        except ValueError as e:
            logger.error(f"Output validation error: {e}")
            sys.exit(1)
        
        # Get audio files with security validation
        try:
            audio_files = get_audio_files(args.input)
            if not audio_files:
                logger.error(f"No valid audio files found in '{args.input}'")
                sys.exit(1)
        except (ValueError, OSError) as e:
            logger.error(f"Error accessing audio files: {e}")
            sys.exit(1)
        
        chapter_mapping = None
        
        # Parse index file if provided
        if args.index:
            try:
                # Validate index file path
                index_path = os.path.abspath(args.index)
                
                # Basic security validation for index file
                if len(index_path) > MAX_PATH_LENGTH:
                    raise ValueError(f"Index file path too long: {len(index_path)}")
                
                if not os.path.exists(index_path):
                    raise ValueError(f"Index file does not exist: {args.index}")
                
                if not os.path.isfile(index_path):
                    raise ValueError(f"Index path is not a file: {args.index}")
                
                if not os.access(index_path, os.R_OK):
                    raise ValueError(f"Index file is not readable: {args.index}")
                
                chapter_mapping, file_order = parse_index_file(args.index)
                
                # Reorder audio files based on index file
                ordered_files = []
                for filename in file_order:
                    matching_file = next((f for f in audio_files if f.name == filename), None)
                    if matching_file:
                        ordered_files.append(matching_file)
                    else:
                        logger.warning(f"File '{filename}' from index not found in input directory")
                
                # Add any remaining files not in the index
                for audio_file in audio_files:
                    if audio_file not in ordered_files:
                        ordered_files.append(audio_file)
                
                audio_files = ordered_files
                logger.info(f"Using custom chapter ordering from '{args.index}'")
                
            except (ValueError, OSError) as e:
                logger.error(f"Error parsing index file: {e}")
                sys.exit(1)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(validated_output)
        if output_dir and not os.path.exists(output_dir):
            try:
                safe_makedirs(output_dir)
            except (OSError, ValueError) as e:
                logger.error(f"Failed to create output directory: {e}")
                sys.exit(1)
        
        # Create m4b file
        success = create_m4b(audio_files, validated_output, chapter_mapping, args.quick, args.title, args.input)
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()