import os
import logging
from io import BytesIO
from flask import Flask, request, send_file, render_template, flash, redirect, url_for
from pydub import AudioSegment
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-here")

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma'}

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_audio_files(speech_file, music_file):
    """
    Process and mix the speech and music audio files.
    
    Args:
        speech_file: The speech audio file
        music_file: The background music file
    
    Returns:
        BytesIO: The mixed audio as MP3 bytes
    """
    try:
        # Load audio files
        logging.debug("Loading speech audio...")
        speech = AudioSegment.from_file(speech_file)
        
        logging.debug("Loading music audio...")
        music = AudioSegment.from_file(music_file)
        
        # Get speech duration
        speech_duration = len(speech)
        logging.debug(f"Speech duration: {speech_duration}ms")
        
        # Match music duration to speech duration
        if len(music) < speech_duration:
            # Music is shorter than speech, loop it
            logging.debug("Music is shorter than speech, looping...")
            loops_needed = (speech_duration // len(music)) + 1
            music = music * loops_needed
        
        # Trim music to match speech duration exactly
        music = music[:speech_duration]
        logging.debug(f"Adjusted music duration: {len(music)}ms")
        
        # Reduce music volume by 10 dB
        logging.debug("Reducing music volume by 10 dB...")
        music = music - 10
        
        # Apply fade-out effect to music
        fade_duration = min(5000, speech_duration)  # 5 seconds or less if speech is shorter
        logging.debug(f"Applying {fade_duration}ms fade-out to music...")
        music = music.fade_out(fade_duration)
        
        # Overlay speech on top of music
        logging.debug("Mixing speech and music...")
        mixed_audio = music.overlay(speech)
        
        # Export to MP3 in memory
        logging.debug("Exporting mixed audio to MP3...")
        output_buffer = BytesIO()
        mixed_audio.export(output_buffer, format="mp3", bitrate="192k")
        output_buffer.seek(0)
        
        return output_buffer
        
    except Exception as e:
        logging.error(f"Error processing audio files: {str(e)}")
        raise

@app.route('/')
def index():
    """Render the upload form."""
    return render_template('index.html')

@app.route('/mix', methods=['POST'])
def mix_audio():
    """
    Mix speech and background music audio files.
    
    Expects multipart/form-data with:
    - speech: Speech audio file
    - music: Background music file
    
    Returns:
    - Mixed audio as downloadable MP3 file
    """
    try:
        # Check if files are present in request
        if 'speech' not in request.files or 'music' not in request.files:
            if request.content_type and 'multipart/form-data' in request.content_type:
                flash('Both speech and music files are required.', 'error')
                return redirect(url_for('index'))
            return {'error': 'Both speech and music files are required.'}, 400
        
        speech_file = request.files['speech']
        music_file = request.files['music']
        
        # Check if files were actually selected
        if speech_file.filename == '' or music_file.filename == '':
            if request.content_type and 'multipart/form-data' in request.content_type:
                flash('Please select both speech and music files.', 'error')
                return redirect(url_for('index'))
            return {'error': 'Please select both speech and music files.'}, 400
        
        # Validate file types
        if not (allowed_file(speech_file.filename) and allowed_file(music_file.filename)):
            error_msg = f'Invalid file type. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            if request.content_type and 'multipart/form-data' in request.content_type:
                flash(error_msg, 'error')
                return redirect(url_for('index'))
            return {'error': error_msg}, 400
        
        logging.debug(f"Processing files: speech={speech_file.filename}, music={music_file.filename}")
        
        # Process audio files
        mixed_audio_buffer = process_audio_files(speech_file, music_file)
        
        # Generate output filename
        speech_name = secure_filename(speech_file.filename or "speech").rsplit('.', 1)[0]
        music_name = secure_filename(music_file.filename or "music").rsplit('.', 1)[0]
        output_filename = f"mixed_{speech_name}_{music_name}.mp3"
        
        logging.debug(f"Sending mixed audio file: {output_filename}")
        
        # Return the mixed audio file
        return send_file(
            mixed_audio_buffer,
            as_attachment=True,
            download_name=output_filename,
            mimetype='audio/mpeg'
        )
        
    except Exception as e:
        error_msg = f'Error processing audio files: {str(e)}'
        logging.error(error_msg)
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            flash(error_msg, 'error')
            return redirect(url_for('index'))
        return {'error': error_msg}, 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    error_msg = "File too large. Maximum size is 100MB."
    if request.content_type and 'multipart/form-data' in request.content_type:
        flash(error_msg, 'error')
        return redirect(url_for('index'))
    return {'error': error_msg}, 413

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
