import os
import logging
import requests
from io import BytesIO
from flask import Flask, request, send_file, render_template, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from urllib.parse import urlparse
from pydub import AudioSegment

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1) # needed for url_for to generate with https

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma'}

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def download_audio_from_url(url):
    """Download audio file from URL and return as BytesIO."""
    try:
        logging.debug(f"Downloading audio from URL: {url}")
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        if not any(audio_type in content_type.lower() for audio_type in ['audio', 'mpeg', 'mp3', 'wav', 'ogg']):
            # Try to validate by URL extension if content-type is unclear
            parsed_url = urlparse(url)
            if not any(ext in parsed_url.path.lower() for ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac']):
                raise ValueError(f"URL does not appear to be an audio file: {url}")
        
        # Download content to BytesIO
        audio_buffer = BytesIO()
        for chunk in response.iter_content(chunk_size=8192):
            audio_buffer.write(chunk)
        audio_buffer.seek(0)
        
        return audio_buffer
        
    except requests.RequestException as e:
        raise ValueError(f"Failed to download audio from URL {url}: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error processing URL {url}: {str(e)}")

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
        fade_duration = min(2000, speech_duration)  # 2 seconds or less if speech is shorter
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

@app.route('/health')
def health_check():
    """Health check endpoint for deployment."""
    return {'status': 'healthy', 'message': 'Audio Mixer API is running'}, 200

@app.route('/mix', methods=['POST'])
def mix_audio():
    """
    Mix speech and background music audio files.
    
    Accepts either:
    - speech_url and music_url: URLs to audio files
    - speech and music: Uploaded audio files (multipart/form-data)
    
    Returns:
    - Mixed audio as downloadable MP3 file
    """
    try:
        speech_file = None
        music_file = None
        speech_name = "speech"
        music_name = "music"
        
        # Check if URLs are provided
        speech_url = request.form.get('speech_url', '').strip()
        music_url = request.form.get('music_url', '').strip()
        
        if speech_url and music_url:
            # URL input mode
            logging.debug("Using URL input mode")
            speech_file = download_audio_from_url(speech_url)
            music_file = download_audio_from_url(music_url)
            speech_name = urlparse(speech_url).path.split('/')[-1].split('.')[0] or "speech"
            music_name = urlparse(music_url).path.split('/')[-1].split('.')[0] or "music"
            
        else:
            # File upload mode
            logging.debug("Using file upload mode")
            
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
            
            speech_name = secure_filename(speech_file.filename or "speech").rsplit('.', 1)[0]
            music_name = secure_filename(music_file.filename or "music").rsplit('.', 1)[0]
        
        logging.debug(f"Processing audio: speech={speech_name}, music={music_name}")
        
        # Process audio files
        mixed_audio_buffer = process_audio_files(speech_file, music_file)
        
        # Generate output filename
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

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    logging.error(f"Internal server error: {str(e)}")
    return {'error': 'Internal server error'}, 500

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    try:
        import models  # noqa: F401
        db.create_all()
    except ImportError:
        # Models file doesn't exist or has import issues, skip table creation
        pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)