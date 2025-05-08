#!/usr/bin/env python3
"""
Audio Transcription Tool (GUI Version)
-------------------------------------
An elegant, Apple-style dark GUI for the audio transcription tool.
"""

import os
import sys
import platform
import subprocess
import time
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText
import traceback

# Function to check and install dependencies
def check_dependencies(status_callback=None):
    """Check and install required dependencies based on OS detection."""
    if status_callback:
        status_callback("Checking system dependencies...")
    
    system = platform.system().lower()
    
    # Check if pip is installed
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        if status_callback:
            status_callback("Error: pip is not installed. Please install pip first.")
        return False
    
    # Install Python dependencies
    if status_callback:
        status_callback("Installing required Python packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "SpeechRecognition", "pydub"])
    except subprocess.CalledProcessError:
        if status_callback:
            status_callback("Error installing Python dependencies. Please install manually.")
        return False
    
    # Check and install ffmpeg based on OS
    if status_callback:
        status_callback("Checking for FFmpeg...")
    
    ffmpeg_installed = False
    try:
        subprocess.check_call(["ffmpeg", "-version"], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL)
        ffmpeg_installed = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        ffmpeg_installed = False
    
    if not ffmpeg_installed:
        if status_callback:
            status_callback("FFmpeg not found. Attempting to install FFmpeg...")
        
        if system == "linux":
            # Try to detect package manager
            if os.path.exists("/usr/bin/apt"):
                if status_callback:
                    status_callback("Detected Ubuntu/Debian. Installing FFmpeg...")
                subprocess.call(["sudo", "apt", "update"])
                subprocess.call(["sudo", "apt", "install", "-y", "ffmpeg"])
            elif os.path.exists("/usr/bin/dnf"):
                if status_callback:
                    status_callback("Detected Fedora/RHEL. Installing FFmpeg...")
                subprocess.call(["sudo", "dnf", "install", "-y", "ffmpeg"])
            elif os.path.exists("/usr/bin/pacman"):
                if status_callback:
                    status_callback("Detected Arch Linux. Installing FFmpeg...")
                subprocess.call(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"])
            else:
                if status_callback:
                    status_callback("Could not detect package manager. Please install FFmpeg manually.")
                return False
        elif system == "darwin":
            # macOS - try to use Homebrew
            try:
                subprocess.check_call(["brew", "--version"], 
                                    stdout=subprocess.DEVNULL, 
                                    stderr=subprocess.DEVNULL)
                if status_callback:
                    status_callback("Installing FFmpeg via Homebrew...")
                subprocess.call(["brew", "install", "ffmpeg"])
            except (subprocess.CalledProcessError, FileNotFoundError):
                if status_callback:
                    status_callback("Homebrew not found. Please install Homebrew and then FFmpeg manually.")
                return False
        elif system == "windows":
            if status_callback:
                status_callback("On Windows, please download FFmpeg from https://ffmpeg.org/download.html")
                status_callback("and add it to your PATH environment variable.")
            return False
        else:
            if status_callback:
                status_callback(f"Unsupported OS: {system}. Please install FFmpeg manually.")
            return False
    
    # Try loading the libraries
    try:
        global sr, AudioSegment, split_on_silence
        import speech_recognition as sr
        from pydub import AudioSegment
        from pydub.silence import split_on_silence
        if status_callback:
            status_callback("All dependencies installed successfully!")
        return True
    except ImportError as e:
        if status_callback:
            status_callback(f"Error loading Python libraries: {str(e)}")
        return False

# Audio processing functions
def convert_to_wav(audio_path, status_callback=None):
    """Convert audio file to WAV format if it's not already."""
    if audio_path.endswith('.wav'):
        return audio_path
    
    filename = os.path.splitext(os.path.basename(audio_path))[0]
    output_path = f"{filename}_converted.wav"
    
    if status_callback:
        status_callback(f"Converting {audio_path} to WAV format...")
    
    audio = AudioSegment.from_file(audio_path)
    audio.export(output_path, format="wav")
    
    if status_callback:
        status_callback(f"Conversion complete: {output_path}")
    
    return output_path

def transcribe_large_audio(audio_path, status_callback=None, min_silence_len=500, silence_thresh=-40):
    """
    Split the audio file into chunks and apply speech recognition on each chunk.
    """
    # Load the audio file
    if status_callback:
        status_callback(f"Loading audio file: {audio_path}")
    sound = AudioSegment.from_wav(audio_path)
    
    # Split audio where silence is detected
    if status_callback:
        status_callback("Splitting audio into chunks based on silence...")
    chunks = split_on_silence(
        sound,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh
    )
    
    # If no chunks were detected (continuous speech), use the whole audio
    if not chunks:
        if status_callback:
            status_callback("No silence detected for splitting. Processing entire audio...")
        chunks = [sound]
    
    # Initialize recognizer
    recognizer = sr.Recognizer()
    full_text = ""
    
    if status_callback:
        status_callback(f"Processing {len(chunks)} audio chunks...")
    
    # Process each chunk
    for i, chunk in enumerate(chunks):
        # Create a silence chunk for padding
        silence_chunk = AudioSegment.silent(duration=500)  # 500ms silence
        
        # Add padding to the chunk to improve recognition accuracy
        audio_chunk = silence_chunk + chunk + silence_chunk
        
        # Export the chunk to a temporary WAV file
        chunk_filename = f"temp_chunk_{i}.wav"
        audio_chunk.export(chunk_filename, format="wav")
        
        # Use the recognizer to transcribe the chunk
        with sr.AudioFile(chunk_filename) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data)
                full_text += text + " "
                if status_callback:
                    status_callback(f"Chunk {i+1}/{len(chunks)}: Transcribed successfully")
            except sr.UnknownValueError:
                if status_callback:
                    status_callback(f"Chunk {i+1}/{len(chunks)}: No speech detected")
            except sr.RequestError as e:
                if status_callback:
                    status_callback(f"Chunk {i+1}/{len(chunks)}: Could not request results; {e}")
        
        # Remove the temporary file
        os.remove(chunk_filename)
    
    return full_text.strip()

def transcribe_audio(audio_path, output_path=None, status_callback=None):
    """
    Main function to handle audio transcription.
    """
    start_time = time.time()
    
    # Convert to WAV if needed
    wav_path = convert_to_wav(audio_path, status_callback)
    
    # Default output path
    if not output_path:
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_path = f"{base_name}_transcription.txt"
    
    # Transcribe the audio
    if status_callback:
        status_callback(f"Starting transcription of {wav_path}...")
    transcription = transcribe_large_audio(wav_path, status_callback)
    
    # Save the transcription
    with open(output_path, "w") as file:
        file.write(transcription)
    
    # Clean up temporary WAV file if conversion was done
    if wav_path != audio_path:
        os.remove(wav_path)
    
    elapsed_time = time.time() - start_time
    if status_callback:
        status_callback(f"Transcription completed in {elapsed_time:.2f} seconds!")
        status_callback(f"Transcription saved to: {output_path}")
    
    return output_path

class AudioTranscriberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Transcriber")
        self.root.geometry("800x600")
        self.setup_ui()
        
        # Set dark mode theme
        self.set_dark_theme()
        
        # Check dependencies in background
        threading.Thread(target=self.init_dependencies, daemon=True).start()
    
    def set_dark_theme(self):
        """Apply Apple-style dark theme to the UI"""
        # Define colors
        bg_color = "#1E1E1E"  # Dark background
        text_color = "#FFFFFF"  # White text
        accent_color = "#0A84FF"  # Apple blue
        secondary_bg = "#2D2D2D"  # Slightly lighter background
        button_bg = "#323232"  # Button background
        button_active = "#454545"  # Button when clicked
        
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('default')
        
        # Configure colors
        style.configure('TFrame', background=bg_color)
        style.configure('TButton', background=button_bg, foreground=text_color, borderwidth=0)
        style.map('TButton', background=[('active', button_active)])
        style.configure('TLabel', background=bg_color, foreground=text_color)
        style.configure('Header.TLabel', background=bg_color, foreground=text_color, font=('Helvetica', 16, 'bold'))
        style.configure('TProgressbar', background=accent_color, troughcolor=secondary_bg)
        
        # Configure root window
        self.root.configure(bg=bg_color)
        
        # Apply to all children
        for widget in self.root.winfo_children():
            if widget.winfo_class() == 'Text' or widget.winfo_class() == 'ScrolledText':
                widget.configure(bg=secondary_bg, fg=text_color, insertbackground=text_color)
            elif widget.winfo_class() == 'TFrame':
                widget.configure(style='TFrame')
    
    def init_dependencies(self):
        """Initialize dependencies in background"""
        self.update_status("Checking dependencies...")
        success = check_dependencies(self.update_status)
        if success:
            self.update_status("Ready to transcribe audio.")
            self.enable_controls()
        else:
            self.update_status("Failed to initialize dependencies. See log for details.")
    
    def setup_ui(self):
        """Set up the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_label = ttk.Label(main_frame, text="Audio Transcriber", style='Header.TLabel')
        header_label.pack(pady=(0, 20))
        
        # File selection frame
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=10)
        
        self.file_path_var = tk.StringVar()
        file_path_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, width=50)
        file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_button = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        browse_button.pack(side=tk.RIGHT)
        
        # Output file frame
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(output_frame, text="Output File (optional):").pack(side=tk.LEFT, padx=(0, 10))
        
        self.output_path_var = tk.StringVar()
        output_path_entry = ttk.Entry(output_frame, textvariable=self.output_path_var, width=40)
        output_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        output_browse_button = ttk.Button(output_frame, text="Browse", command=self.browse_output)
        output_browse_button.pack(side=tk.RIGHT)
        
        # Transcription button
        self.transcribe_button = ttk.Button(main_frame, text="Transcribe Audio", command=self.start_transcription)
        self.transcribe_button.pack(pady=20)
        self.transcribe_button.state(['disabled'])  # Initially disabled
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=10)
        
        # Status and log
        ttk.Label(main_frame, text="Status:").pack(anchor=tk.W, pady=(10, 5))
        
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
    
    def enable_controls(self):
        """Enable UI controls after dependencies are loaded"""
        self.transcribe_button.state(['!disabled'])
    
    def browse_file(self):
        """Open file dialog to select audio file"""
        filetypes = (
            ('Audio files', '*.mp3 *.wav *.m4a *.flac *.aac'),
            ('All files', '*.*')
        )
        
        filename = filedialog.askopenfilename(
            title='Select an audio file',
            initialdir='/',
            filetypes=filetypes
        )
        
        if filename:
            self.file_path_var.set(filename)
            # Set default output path
            base_name = os.path.splitext(os.path.basename(filename))[0]
            output_path = os.path.join(os.path.dirname(filename), f"{base_name}_transcription.txt")
            self.output_path_var.set(output_path)
    
    def browse_output(self):
        """Open file dialog to select output file"""
        filename = filedialog.asksaveasfilename(
            title='Save transcription as',
            defaultextension='.txt',
            filetypes=(('Text files', '*.txt'), ('All files', '*.*'))
        )
        
        if filename:
            self.output_path_var.set(filename)
    
    def update_status(self, message):
        """Update the status log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def start_transcription(self):
        """Start the transcription process in a separate thread"""
        audio_path = self.file_path_var.get()
        output_path = self.output_path_var.get() if self.output_path_var.get() else None
        
        if not audio_path:
            self.update_status("Error: No audio file selected.")
            return
        
        if not os.path.exists(audio_path):
            self.update_status(f"Error: File does not exist: {audio_path}")
            return
        
        # Disable controls during transcription
        self.transcribe_button.state(['disabled'])
        self.progress.start()
        
        # Clear log
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Start transcription in a separate thread
        threading.Thread(
            target=self._run_transcription,
            args=(audio_path, output_path),
            daemon=True
        ).start()
    
    def _run_transcription(self, audio_path, output_path):
        """Run the transcription process"""
        try:
            transcribe_audio(audio_path, output_path, self.update_status)
            self.root.after(0, self._transcription_complete)
        except Exception as e:
            self.root.after(0, lambda: self._transcription_error(str(e), traceback.format_exc()))
    
    def _transcription_complete(self):
        """Called when transcription is complete"""
        self.progress.stop()
        self.transcribe_button.state(['!disabled'])
        self.update_status("Transcription complete!")
    
    def _transcription_error(self, error, traceback_info):
        """Called when transcription encounters an error"""
        self.progress.stop()
        self.transcribe_button.state(['!disabled'])
        self.update_status(f"Error during transcription: {error}")
        self.update_status("Technical details:")
        self.update_status(traceback_info)

def main():
    # Create the Tkinter app
    root = tk.Tk()
    app = AudioTranscriberApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
