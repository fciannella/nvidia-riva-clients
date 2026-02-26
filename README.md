# Riva Transcription Service

A modern web application for audio transcription using NVIDIA Riva, featuring speaker diarization, automatic audio conversion, and a beautiful React UI.

## Features

- 🎙️ **Audio Transcription**: High-quality speech-to-text using NVIDIA Riva
- 👥 **Speaker Diarization**: Identify and label different speakers in conversations
- 🔄 **Auto-Conversion**: Automatically convert any audio format to WAV using ffmpeg
- ⏱️ **Word-Level Timestamps**: Get precise timing for each word
- 📊 **Confidence Scores**: See transcription confidence for quality assessment
- 💾 **JSON Export**: Download complete transcription data as JSON
- 🎨 **Modern UI**: Beautiful React + TypeScript interface
- 💬 **AI Q&A**: Ask questions about transcripts using LangChain and LLM
- 🔄 **Multi-Turn Conversations**: Have back-and-forth discussions about the content
- 🐳 **Docker Support**: One-command deployment with Docker Compose

## 🚀 Quick Start with Docker (Recommended)

The easiest way to run the entire application:

```bash
# 1. Clone and navigate to the project
git clone <repository-url>
cd riva-clients-fciannella

# 2. Set up environment variables
cp .env.example .env
nano .env  # Add your credentials

# 3. Build and run everything
docker-compose up --build

# 4. Access the app at http://localhost:8000
```

That's it! Both backend and frontend are running in a single container.

See **[DOCKER.md](DOCKER.md)** for detailed Docker documentation.

## Architecture

```
├── offline-transcribe.py   # Core transcription CLI tool
├── api.py                   # FastAPI backend server
└── frontend/                # React + Vite + TypeScript UI
    ├── src/
    │   ├── App.tsx         # Main application component
    │   └── App.css         # Styling
    └── package.json
```

## Prerequisites

### System Requirements
- Python 3.8+
- Node.js 20+ and npm
- ffmpeg (for audio conversion)

### Install ffmpeg
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### Environment Variables

Create a `.env` file in the project root with your Riva credentials:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your actual credentials
nano .env  # or use your preferred editor
```

#### Deployment Types

This application supports three Riva deployment types:

**1. NVCF (NVIDIA Cloud Functions) - Default**
```bash
RIVA_DEPLOYMENT_TYPE=nvcf
RIVA_USE_SSL=true
RIVA_URI=grpc.nvcf.nvidia.com:443
RIVA_BEARER_TOKEN=nvapi-your-token-here
RIVA_FUNCTION_ID=your-function-id
RIVA_FUNCTION_VERSION_ID=your-version-id
```

**2. Self-Hosted Riva**
```bash
RIVA_DEPLOYMENT_TYPE=self-hosted
RIVA_USE_SSL=false
RIVA_URI=localhost:50051
# Optional: RIVA_SSL_CERT=/path/to/cert.pem
# Optional: RIVA_API_KEY=your-api-key
```

**3. Cloud-Hosted Riva**
```bash
RIVA_DEPLOYMENT_TYPE=cloud
RIVA_USE_SSL=true
RIVA_URI=riva.yourcompany.com:443
RIVA_API_KEY=your-api-key
# Or: RIVA_BEARER_TOKEN=your-bearer-token
```

**LLM Configuration (for Q&A and speaker naming features):**
```bash
BASE_URL=https://llms.flashlit.ai:5000/v1
MODEL_NAME=nvcf-gpt-oss-120b
OPENAI_API_KEY=your_openai_api_key
```

**Note:** The `.env` file is gitignored for security - never commit credentials to version control!

See `.env.example` for detailed configuration examples and all available options.

#### Switching Between Deployment Types

To switch from NVCF to a self-hosted Riva instance, simply update your `.env`:

```bash
# Change deployment type
RIVA_DEPLOYMENT_TYPE=self-hosted

# Update connection settings
RIVA_URI=localhost:50051
RIVA_USE_SSL=false

# Comment out NVCF-specific variables (they won't be used)
# RIVA_BEARER_TOKEN=...
# RIVA_FUNCTION_ID=...
# RIVA_FUNCTION_VERSION_ID=...
```

Then restart your application. No code changes needed!

## Installation

### 1. Backend Setup

Install Python dependencies (using uv):
```bash
uv pip install -r requirements-api.txt
```

Or using standard pip:
```bash
pip install fastapi uvicorn python-multipart riva-client
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### Option 1: Run Both Services Together

**Terminal 1 - Start Backend API:**
```bash
source .venv/bin/activate && python api.py
```
The API will be available at http://localhost:8000

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run dev
```
The UI will be available at http://localhost:5173

### Option 2: Use the CLI Tool Directly

```bash
# Basic transcription
source .venv/bin/activate && python offline-transcribe.py audio.wav

# With speaker diarization
source .venv/bin/activate && python offline-transcribe.py --diarize --max-speakers 2 interview.wav

# Convert and transcribe
source .venv/bin/activate && python offline-transcribe.py --convert audio.mp3

# Save to JSON
source .venv/bin/activate && python offline-transcribe.py --diarize --output result.json interview.wav

# All options combined
source .venv/bin/activate && python offline-transcribe.py --convert --diarize --max-speakers 3 --output out.json audio.m4a
```

## CLI Usage

```
usage: offline-transcribe.py [-h] [--convert] [--diarize] [--max-speakers MAX_SPEAKERS] [--output OUTPUT] audio_file

Transcribe a WAV file using NVIDIA Riva (offline)

positional arguments:
  audio_file            Path to audio file to transcribe

options:
  -h, --help            show this help message and exit
  --convert             Convert input file to WAV (mono, 16-bit, 22050Hz) using ffmpeg before transcription
  --diarize, --speaker-diarization
                        Enable speaker diarization to identify different speakers
  --max-speakers MAX_SPEAKERS
                        Maximum number of speakers to identify (default: 8, only used with --diarize)
  --output OUTPUT, -o OUTPUT
                        Save transcription to JSON file (if not specified, prints to stdout)
```

## API Endpoints

### `POST /transcribe`

Upload an audio file for transcription.

**Request:**
- `file`: Audio file (multipart/form-data)
- `diarize`: Enable speaker diarization (boolean, default: false)
- `max_speakers`: Maximum number of speakers (int, default: 8)
- `auto_convert`: Auto-convert to WAV format (boolean, default: true)

**Response:**
```json
{
  "audio_file": "path/to/file.wav",
  "diarization_enabled": true,
  "max_speakers": 2,
  "segments": [
    {
      "transcript": "Hello, how are you?",
      "confidence": 0.95,
      "words": [
        {
          "word": "Hello",
          "start_time": 0.5,
          "end_time": 0.8,
          "confidence": 0.98,
          "speaker": 1
        }
      ]
    }
  ],
  "formatted_transcript": [
    {
      "speaker": 1,
      "text": "Hello, how are you?"
    }
  ],
  "metadata": {
    "original_filename": "audio.mp3",
    "file_size_bytes": 1234567,
    "converted": true,
    "diarization_enabled": true,
    "max_speakers": 2
  }
}
```

### `POST /question_answer`

Ask questions about a transcript using LLM.

**Request:**
```json
{
  "session_id": "optional-session-id",
  "transcript": "full transcript text",
  "question": "What were the main topics discussed?"
}
```

**Response:**
```json
{
  "session_id": "uuid-session-id",
  "question": "What were the main topics discussed?",
  "answer": "The main topics discussed were...",
  "conversation_history": [
    {
      "role": "user",
      "content": "What were the main topics discussed?"
    },
    {
      "role": "assistant",
      "content": "The main topics discussed were..."
    }
  ]
}
```

### `GET /session/{session_id}`

Retrieve conversation history for a session.

### `DELETE /session/{session_id}`

Delete a conversation session.

## Web UI Features

### Upload Section
- Drag-and-drop or click to select audio files
- Supports all audio formats (auto-converts to WAV)
- Shows file size information

### Transcription Options
- Toggle speaker diarization on/off
- Adjust maximum number of speakers (2-20)
- Real-time loading feedback

### Results Display
- **Formatted Transcript**: Color-coded speaker labels for easy reading
- **Metadata**: File info, conversion status, settings used
- **Detailed View**: Word-level timestamps and confidence scores
- **Download Button**: Export complete JSON data

### Speaker Visualization
- Each speaker gets a unique color
- Hover over words to see timestamps and confidence
- Clean, readable layout with visual separation

### Q&A Chat Interface
- **Ask Questions**: Query the transcript using natural language
- **Multi-Turn Conversations**: Follow-up questions maintain context
- **Smart Suggestions**: Get suggested questions to start
- **Conversation History**: View full chat history
- **Session Management**: Clear chat to start fresh

## Development

### Backend Development
```bash
# Run with auto-reload
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Build for Production
```bash
cd frontend
npm run build
```

## Troubleshooting

### Issue: "ffmpeg not found"
Install ffmpeg using your package manager (see Prerequisites section)

### Issue: "Import riva.client could not be resolved"
Make sure you've installed the riva-client package:
```bash
uv pip install riva-client
```

### Issue: CORS errors in browser
Ensure the backend API is running on port 8000 and the frontend is accessing the correct URL.

### Issue: Speaker diarization not working
- Check that your Riva server/API supports speaker diarization
- Verify the model is deployed correctly
- Try adjusting the `--max-speakers` parameter

## Audio Format Requirements

The transcription service works best with:
- **Format**: WAV (auto-conversion available for other formats)
- **Sample Rate**: 22050 Hz (auto-converted)
- **Channels**: Mono (auto-converted)
- **Bit Depth**: 16-bit (auto-converted)

Don't worry if your file doesn't meet these specs - the `--convert` flag handles it automatically!

## License

MIT

## Credits

- Powered by [NVIDIA Riva](https://developer.nvidia.com/riva)
- Built with [FastAPI](https://fastapi.tiangolo.com/)
- UI built with [React](https://react.dev/) + [Vite](https://vitejs.dev/) + [TypeScript](https://www.typescriptlang.org/)

