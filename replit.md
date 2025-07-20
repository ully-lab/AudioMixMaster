# Audio Mixer API

## Overview

This repository contains a Flask-based web application that provides an audio mixing service. The application allows users to upload speech and background music files, which are then automatically mixed together with professional audio processing techniques including duration matching, fade effects, and volume balancing.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: HTML templates with Bootstrap for styling
- **UI Components**: Single-page web interface with file upload forms
- **Styling**: Bootstrap dark theme with Feather icons for modern UI
- **Client-side Features**: File upload validation and flash message display

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Audio Processing**: PyDub library for audio manipulation and mixing
- **File Handling**: Werkzeug utilities for secure file uploads
- **Session Management**: Flask sessions with configurable secret key

## Key Components

### Core Application (`app.py`)
- **Flask Application**: Main web server with route handling
- **Audio Processing Engine**: Core mixing functionality using PyDub
- **File Upload Handler**: Secure file upload with extension validation
- **Error Handling**: Comprehensive logging and flash message system

### Entry Point (`main.py`)
- **Application Runner**: Development server configuration
- **Host Configuration**: Configured for 0.0.0.0:5000 with debug mode

### User Interface (`templates/index.html`)
- **Upload Interface**: Form-based file upload for speech and music files
- **Progress Feedback**: Flash message system for user notifications
- **Responsive Design**: Bootstrap-based responsive layout

## Data Flow

1. **File Upload**: Users upload speech and background music files through web interface
2. **Validation**: Server validates file types against allowed extensions (mp3, wav, ogg, flac, m4a, aac, wma)
3. **Audio Processing**: PyDub loads and processes both audio files
4. **Duration Matching**: Music duration is adjusted to match speech duration
5. **Mixing**: Audio files are combined with volume balancing and fade effects
6. **Output Generation**: Mixed audio is returned as MP3 format
7. **File Delivery**: Processed audio is served as downloadable file

## External Dependencies

### Python Libraries
- **Flask**: Web framework for HTTP handling and templating
- **PyDub**: Audio file manipulation and processing
- **Werkzeug**: WSGI utilities and secure filename handling

### Frontend Dependencies
- **Bootstrap**: CSS framework for responsive UI design
- **Feather Icons**: Icon library for UI elements

### System Requirements
- **Audio Codecs**: Requires FFmpeg or similar for audio format support
- **File System**: Temporary file handling for upload processing

## Deployment Strategy

### Development Environment
- **Debug Mode**: Enabled for development with hot reloading
- **Host Binding**: Configured for 0.0.0.0 to allow external access
- **Port Configuration**: Standard port 5000 for Flask development

### Configuration Management
- **Environment Variables**: Session secret key configurable via environment
- **Upload Limits**: 100MB maximum file size limit
- **Security**: Secure filename handling and file type validation

### Scalability Considerations
- **Stateless Design**: No persistent data storage required
- **Memory Usage**: Audio processing happens in-memory with BytesIO streams
- **File Cleanup**: Temporary file handling for upload processing

## Notes for Development

The application is designed as a simple audio mixing service with minimal dependencies. The architecture supports easy extension for additional audio processing features or integration with cloud storage services. The current implementation processes files in-memory, making it suitable for moderate file sizes but may require optimization for large-scale deployment.