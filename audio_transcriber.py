#!/usr/bin/env python3
"""
Audio Transcription Tool
------------------------
This script transcribes speech from audio files to text.
It supports various audio formats (WAV, MP3, etc.) and saves the transcription to a text file.
Features automatic OS detection, dependency installation, redundant processing methods,
and comprehensive error handling for maximum reliability.
"""

import os
import sys
import glob
import platform
import subprocess
import argparse
import time
import json
import tempfile
import hashlib
from pathlib import Path
import signal

# Set up timeouts for unresponsive operations
class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

# Register the signal handler for SIGALRM
signal.signal(signal.SIGALRM, timeout_handler)

# Function to check and install dependencies
def check_dependencies():
    """Check and install required dependencies based on OS detection."""
    system = platform.system().lower()
    
    # Check if pip is installed
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], 
                              stdout=subprocess.DEVNULL, 
                              stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("Error: pip is not installed. Please install pip first.")
        sys.exit(1)
    
    # Install Python dependencies
    print("Installing required Python packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "SpeechRecognition", "pydub"])
    except subprocess.CalledProcessError:
        print("Error installing Python dependencies. Please try manually:")
        print("pip install SpeechRecognition pydub")
        sys.exit(1)
    
    # Check and install ffmpeg based on OS
    print("Checking for FFmpeg...")
    ffmpeg_installed = False
    
    try:
        subprocess.check_call(["ffmpeg", "-version"], 
                              stdout=subprocess.DEVNULL, 
                              stderr=subprocess.DEVNULL)
        ffmpeg_installed = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        ffmpeg_installed = False
    
    if not ffmpeg_installed:
        print("FFmpeg not found. Attempting to install FFmpeg...")
        
        if system == "linux":
            # Try to detect package manager
            if os.path.exists("/usr/bin/apt"):
                print("Detected Debian/Ubuntu system")
                subprocess.call(["sudo", "apt", "update"])
                subprocess.call(["sudo", "apt", "install", "-y", "ffmpeg"])
            elif os.path.exists("/usr/bin/dnf"):
                print("Detected Fedora/RHEL system")
                subprocess.call(["sudo", "dnf", "install", "-y", "ffmpeg"])
            elif os.path.exists("/usr/bin/pacman"):
                print("Detected Arch Linux system")
                subprocess.call(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"])
            else:
                print("Could not detect package manager. Please install FFmpeg manually.")
        elif system == "darwin":
            # macOS - try to use Homebrew
            try:
                subprocess.check_call(["brew", "--version"], 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL)
                print("Installing FFmpeg via Homebrew...")
                subprocess.call(["brew", "install", "ffmpeg"])
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Homebrew not found. Please install Homebrew and then FFmpeg manually:")
                print("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
                print("  brew install ffmpeg")
        elif system == "windows":
            print("On Windows, please download FFmpeg from https://ffmpeg.org/download.html")
            print("and add it to your PATH environment variable.")
        else:
            print(f"Unsupported OS: {system}. Please install FFmpeg manually.")

# Now import the modules that require the dependencies
try:
    import speech_recognition as sr
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
except ImportError:
    print("Required Python packages not found. Installing dependencies...")
    check_dependencies()
    # Try importing again
    import speech_recognition as sr
    from pydub import AudioSegment
    from pydub.silence import split_on_silence

def convert_to_wav(audio_path):
    """
    Convert audio file to WAV format if it's not already.
    Includes multiple conversion methods for redundancy.
    """
    if audio_path.endswith('.wav'):
        return audio_path
    
    filename = os.path.splitext(os.path.basename(audio_path))[0]
    output_path = f"{filename}_converted.wav"
    temp_output_path = f"{filename}_temp.wav"
    
    # Primary conversion method using pydub
    try:
        print(f"Attempting to convert {audio_path} to WAV using primary method...")
        audio = AudioSegment.from_file(audio_path)
        audio.export(output_path, format="wav")
        print(f"Converted {audio_path} to {output_path}")
        return output_path
    except Exception as e:
        print(f"Primary conversion method failed: {str(e)}")
        print("Trying backup conversion method...")
        
        # Backup conversion method using ffmpeg directly
        try:
            # Determine platform-specific command execution
            if platform.system().lower() == "windows":
                subprocess.check_call(
                    ["ffmpeg", "-i", audio_path, "-acodec", "pcm_s16le", "-ar", "44100", temp_output_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                subprocess.check_call(
                    ["ffmpeg", "-i", audio_path, "-acodec", "pcm_s16le", "-ar", "44100", temp_output_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # Verify the backup conversion worked
            if os.path.exists(temp_output_path) and os.path.getsize(temp_output_path) > 0:
                os.rename(temp_output_path, output_path)
                print(f"Backup conversion successful: {output_path}")
                return output_path
            else:
                raise Exception("Backup conversion produced invalid file")
                
        except Exception as backup_error:
            print(f"Backup conversion also failed: {str(backup_error)}")
            print("Returning original file for last-resort processing attempt...")
            return audio_path  # Return original as last resort

def transcribe_large_audio(audio_path, min_silence_len=500, silence_thresh=-40):
    """
    Split the audio file into chunks and apply speech recognition on each chunk.
    Includes redundancy with multiple recognition services and error recovery.
    
    Args:
        audio_path: Path to the WAV audio file
        min_silence_len: Minimum length of silence (in ms) to be detected as a split point
        silence_thresh: Silence threshold in dBFS
        
    Returns:
        Full transcription text
    """
    # Load the audio file with error handling
    print(f"Loading audio file: {audio_path}")
    try:
        sound = AudioSegment.from_wav(audio_path)
    except Exception as e:
        print(f"Error loading audio file: {str(e)}")
        # Last resort attempt - try loading with different approach
        try:
            print("Attempting alternative loading method...")
            sound = AudioSegment.from_file(audio_path)
            print("Alternative loading successful")
        except Exception as alt_error:
            print(f"Alternative loading also failed: {str(alt_error)}")
            print("Cannot process audio file. Returning empty transcription.")
            return ""
    
    # Try multiple silence detection parameters if initial attempt produces poor results
    print("Splitting audio into chunks based on silence...")
    
    # Primary chunking attempt
    chunks = split_on_silence(
        sound,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh
    )
    
    # If very few chunks detected, try with different parameters
    if len(chunks) < 2:
        print("Few chunks detected. Trying alternative silence parameters...")
        # Try more aggressive silence detection
        alt_chunks = split_on_silence(
            sound,
            min_silence_len=300,  # Shorter silence detection
            silence_thresh=-35    # Less strict silence threshold
        )
        
        # Use alternative chunks if they seem better
        if len(alt_chunks) > len(chunks):
            print(f"Using alternative chunking method ({len(alt_chunks)} chunks vs {len(chunks)})")
            chunks = alt_chunks
    
    # If still no chunks were detected, use fixed-length chunking as final fallback
    if not chunks:
        print("No silence detected for splitting. Using fixed-length chunking...")
        # Create 30-second chunks
        chunk_length_ms = 30000
        chunks = [sound[i:i+chunk_length_ms] for i in range(0, len(sound), chunk_length_ms)]
    
    # Initialize primary and backup recognizers
    primary_recognizer = sr.Recognizer()
    backup_recognizer = sr.Recognizer()
    
    # Adjust recognizer parameters for better recognition
    primary_recognizer.energy_threshold = 300
    backup_recognizer.energy_threshold = 300
    
    # Different API settings for backup
    primary_recognizer.pause_threshold = 0.8
    backup_recognizer.pause_threshold = 1.0
    
    full_text = ""
    chunk_files = []
    
    print(f"Processing {len(chunks)} audio chunks...")
    
    # Process each chunk with redundancy
    for i, chunk in enumerate(chunks):
        # Create a silence chunk for padding
        silence_chunk = AudioSegment.silent(duration=500)  # 500ms silence
        
        # Add padding to the chunk to improve recognition accuracy
        audio_chunk = silence_chunk + chunk + silence_chunk
        
        # Export the chunk to a temporary WAV file
        chunk_filename = f"temp_chunk_{i}.wav"
        chunk_files.append(chunk_filename)
        
        try:
            audio_chunk.export(chunk_filename, format="wav")
            
            # Primary recognition attempt with Google
            with sr.AudioFile(chunk_filename) as source:
                audio_data = primary_recognizer.record(source)
                success = False
                
                # Try primary service (Google)
                try:
                    text = primary_recognizer.recognize_google(audio_data)
                    full_text += text + " "
                    print(f"Chunk {i+1}/{len(chunks)}: Transcribed successfully")
                    success = True
                except sr.UnknownValueError:
                    print(f"Chunk {i+1}/{len(chunks)}: No speech detected with primary recognizer")
                except sr.RequestError as e:
                    print(f"Chunk {i+1}/{len(chunks)}: Primary recognizer request error: {e}")
                
                # If primary failed, try backup services
                if not success:
                    try:
                        # Try Sphinx as offline backup
                        print(f"Chunk {i+1}/{len(chunks)}: Trying backup recognizer...")
                        # Attempt to use recognizer_sphinx if available, otherwise continue with fallback
                        try:
                            # Try to import pocketsphinx only if needed
                            import speech_recognition as sr_backup
                            text = backup_recognizer.recognize_sphinx(audio_data)
                            full_text += text + " "
                            print(f"Chunk {i+1}/{len(chunks)}: Backup transcription successful")
                        except (ImportError, AttributeError):
                            # If Sphinx not available, try second Google attempt with different settings
                            text = backup_recognizer.recognize_google(audio_data)
                            full_text += text + " "
                            print(f"Chunk {i+1}/{len(chunks)}: Alternative transcription successful")
                    except Exception as backup_error:
                        print(f"Chunk {i+1}/{len(chunks)}: Backup transcription also failed: {str(backup_error)}")
        except Exception as chunk_error:
            print(f"Error processing chunk {i+1}: {str(chunk_error)}")
    
    # Clean up all temporary files with error handling
    for chunk_file in chunk_files:
        try:
            if os.path.exists(chunk_file):
                os.remove(chunk_file)
        except Exception as e:
            print(f"Warning: Failed to remove temporary file {chunk_file}: {str(e)}")
    
    return full_text.strip()

def transcribe_audio(audio_path, output_path=None):
    """
    Main function to handle audio transcription with comprehensive error handling
    and redundancy for robust operation.
    
    Args:
        audio_path: Path to the audio file
        output_path: Path where to save the transcription
        
    Returns:
        Path to the saved transcription file
    """
    start_time = time.time()
    temp_files = []
    success = False
    backup_output = False
    original_output_path = output_path
    
    try:
        # Auto-detect file path if given a directory
        if os.path.isdir(audio_path):
            print(f"Directory provided instead of file. Scanning for audio files...")
            audio_files = []
            for extension in ['.wav', '.mp3', '.m4a', '.flac', '.aac', '.ogg']:
                audio_files.extend(glob.glob(os.path.join(audio_path, f"*{extension}")))
            
            if audio_files:
                print(f"Found {len(audio_files)} audio files. Using the first one: {audio_files[0]}")
                audio_path = audio_files[0]
            else:
                print(f"No audio files found in directory {audio_path}")
                return None
        
        # Ensure the file exists
        if not os.path.isfile(audio_path):
            print(f"Error: {audio_path} is not a valid file.")
            return None
        
        # Convert to WAV if needed with error handling
        try:
            wav_path = convert_to_wav(audio_path)
            if wav_path != audio_path:
                temp_files.append(wav_path)
        except Exception as conv_error:
            print(f"Warning: Error during conversion: {str(conv_error)}")
            print("Attempting to process original file...")
            wav_path = audio_path
        
        # Default output path
        if not output_path:
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            output_path = f"{base_name}_transcription.txt"
        
        # Backup output path in case primary location isn't writable
        backup_output_path = os.path.join(
            os.path.expanduser("~"), 
            f"audio_transcription_{int(time.time())}.txt"
        )
        
        # Transcribe the audio
        print(f"Starting transcription of {wav_path}...")
        transcription = transcribe_large_audio(wav_path)
        
        # Check if transcription is empty and run recovery if needed
        if not transcription.strip():
            print("Warning: Empty transcription detected. Trying alternative settings...")
            # Try again with different parameters
            transcription = transcribe_large_audio(wav_path, min_silence_len=300, silence_thresh=-35)
        
        # Save the transcription with error handling
        try:
            with open(output_path, "w") as file:
                file.write(transcription)
            print(f"Transcription saved to: {output_path}")
            success = True
        except Exception as save_error:
            print(f"Error saving to {output_path}: {str(save_error)}")
            print(f"Trying backup location: {backup_output_path}")
            
            try:
                with open(backup_output_path, "w") as backup_file:
                    backup_file.write(transcription)
                print(f"Transcription saved to backup location: {backup_output_path}")
                output_path = backup_output_path
                backup_output = True
                success = True
            except Exception as backup_save_error:
                print(f"Error saving to backup location: {str(backup_save_error)}")
                
                # Last resort - print to console
                print("\n--- TRANSCRIPTION RESULT ---\n")
                print(transcription)
                print("\n--- END TRANSCRIPTION ---\n")
                print("Transcription could not be saved to file, but is displayed above.")
        
        # Clean up temporary files with error handling
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as cleanup_error:
                print(f"Warning: Could not remove temporary file {temp_file}: {str(cleanup_error)}")
        
        elapsed_time = time.time() - start_time
        print(f"Transcription completed in {elapsed_time:.2f} seconds!")
        
        # If we had to use backup location, try to copy back to original location
        if backup_output and original_output_path:
            try:
                import shutil
                shutil.copy2(backup_output_path, original_output_path)
                print(f"Successfully copied transcription to original requested location: {original_output_path}")
                output_path = original_output_path
            except Exception as copy_error:
                print(f"Note: Could not copy to original requested location: {str(copy_error)}")
        
        return output_path
    
    except Exception as e:
        print(f"Critical error during transcription: {str(e)}")
        print("Stack trace:")
        import traceback
        traceback.print_exc()
        
        # Clean up any temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        
        return None

def auto_detect_audio_files():
    """
    Automatically scan the current directory for audio files.
    Returns a list of audio files found.
    """
    # Common audio file extensions
    extensions = ['.wav', '.mp3', '.m4a', '.flac', '.aac', '.ogg', '.wma', '.mp4', '.avi', '.mov']
    
    audio_files = []
    for ext in extensions:
        audio_files.extend(glob.glob(f"*{ext}"))
    
    return audio_files

def save_config(config):
    """Save configuration to a JSON file."""
    config_dir = os.path.join(os.path.expanduser("~"), ".audio_transcriber")
    os.makedirs(config_dir, exist_ok=True)
    
    config_path = os.path.join(config_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f)
    
def load_config():
    """Load configuration from a JSON file."""
    config_dir = os.path.join(os.path.expanduser("~"), ".audio_transcriber")
    config_path = os.path.join(config_dir, "config.json")
    
    default_config = {
        "last_used_dir": os.path.expanduser("~"),
        "default_output_dir": os.path.expanduser("~"),
        "auto_detect_files": True,
        "auto_install_deps": True
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            # Merge with defaults for any missing keys
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
        except Exception:
            return default_config
    else:
        return default_config

def main():
    """Main function to parse arguments and handle the audio transcription process."""
    # Load configuration
    config = load_config()
    
    parser = argparse.ArgumentParser(description="Transcribe audio files to text.")
    parser.add_argument("audio_path", nargs="?", help="Path to the audio file to transcribe (optional)")
    parser.add_argument("-o", "--output", help="Path where to save the transcription")
    parser.add_argument("--install-deps", action="store_true", help="Check and install dependencies")
    parser.add_argument("--scan-dir", help="Scan directory for audio files")
    parser.add_argument("--batch", action="store_true", help="Process all audio files in the current directory")
    
    args = parser.parse_args()
    
    # Auto-install dependencies by default unless explicitly disabled
    if config["auto_install_deps"] and not args.install_deps:
        print("Performing automatic dependency check...")
        check_dependencies()
    # Manual dependency check
    elif args.install_deps:
        check_dependencies()
        print("Dependencies check complete.")
        return
    
    # Handle directory scanning
    if args.scan_dir:

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
        sys.exit(0)
