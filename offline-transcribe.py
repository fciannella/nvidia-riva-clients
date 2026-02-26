import argparse
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import riva.client

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def build_auth_from_env() -> riva.client.Auth:
    """Create Riva auth from environment variables, supporting multiple deployment types.

    Environment Variables:
    ----------------------
    Required (all deployments):
    - RIVA_DEPLOYMENT_TYPE: 'nvcf', 'self-hosted', or 'cloud' (default: 'nvcf')
    - RIVA_USE_SSL: 'true' or 'false' (default: 'true')
    - RIVA_URI: Server address with port (e.g., 'localhost:50051')
    
    NVCF-specific (when RIVA_DEPLOYMENT_TYPE=nvcf):
    - RIVA_BEARER_TOKEN: NVCF API token
    - RIVA_FUNCTION_ID: NVCF function ID
    - RIVA_FUNCTION_VERSION_ID: NVCF function version ID
    
    Self-hosted with SSL (when RIVA_DEPLOYMENT_TYPE=self-hosted and RIVA_USE_SSL=true):
    - RIVA_SSL_CERT: Path to SSL certificate file (optional)
    
    Cloud deployment (when RIVA_DEPLOYMENT_TYPE=cloud):
    - RIVA_API_KEY: API key for authentication (optional)
    - RIVA_BEARER_TOKEN: Bearer token for authentication (optional, alternative to API_KEY)
    
    Returns:
        riva.client.Auth: Configured authentication object
        
    Raises:
        ValueError: If required environment variables are missing or invalid
    """
    # Common settings
    deployment_type = os.getenv('RIVA_DEPLOYMENT_TYPE', 'nvcf').lower()
    use_ssl = os.getenv('RIVA_USE_SSL', 'true').lower() == 'true'
    riva_uri = os.getenv('RIVA_URI', 'grpc.nvcf.nvidia.com:443')
    ssl_cert_path = os.getenv('RIVA_SSL_CERT', None)
    
    logger.info(f"🔧 Configuring Riva connection for deployment type: {deployment_type}")
    logger.info(f"📡 Riva URI: {riva_uri}, SSL: {use_ssl}")
    
    # Build SSL cert parameter
    ssl_cert = None
    if ssl_cert_path and os.path.exists(ssl_cert_path):
        ssl_cert = ssl_cert_path
        logger.info(f"🔒 Using SSL certificate: {ssl_cert_path}")
    elif ssl_cert_path:
        logger.warning(f"⚠️  SSL certificate path provided but file not found: {ssl_cert_path}")
    
    # Build metadata based on deployment type
    metadata = []
    
    if deployment_type == 'nvcf':
        # NVCF requires bearer token and function IDs
        bearer_token = os.getenv('RIVA_BEARER_TOKEN', '')
        function_id = os.getenv('RIVA_FUNCTION_ID', '')
        function_version_id = os.getenv('RIVA_FUNCTION_VERSION_ID', '')
        
        if not all([bearer_token, function_id, function_version_id]):
            missing = []
            if not bearer_token:
                missing.append('RIVA_BEARER_TOKEN')
            if not function_id:
                missing.append('RIVA_FUNCTION_ID')
            if not function_version_id:
                missing.append('RIVA_FUNCTION_VERSION_ID')
            raise ValueError(
                f"❌ NVCF deployment requires: {', '.join(missing)}\n"
                f"💡 Tip: Set RIVA_DEPLOYMENT_TYPE=self-hosted or cloud if not using NVCF."
            )
        
        metadata = [
            ['authorization', f'Bearer {bearer_token}'],
            ['function-id', function_id],
            ['function-version-id', function_version_id],
        ]
        logger.info("🔑 Using NVCF authentication with function routing")
    
    elif deployment_type == 'cloud':
        # Cloud deployment might use API key or bearer token
        api_key = os.getenv('RIVA_API_KEY', '')
        bearer_token = os.getenv('RIVA_BEARER_TOKEN', '')
        
        if api_key:
            metadata = [['api-key', api_key]]
            logger.info("🔑 Using API key authentication")
        elif bearer_token:
            metadata = [['authorization', f'Bearer {bearer_token}']]
            logger.info("🔑 Using Bearer token authentication")
        else:
            logger.warning("⚠️  No authentication configured for cloud deployment")
            # metadata remains empty []
    
    elif deployment_type == 'self-hosted':
        # Self-hosted typically doesn't need authentication metadata
        # But check if optional auth is provided
        api_key = os.getenv('RIVA_API_KEY', '')
        if api_key:
            metadata = [['api-key', api_key]]
            logger.info("🔑 Using API key authentication for self-hosted")
        else:
            logger.info("🔓 No authentication metadata for self-hosted deployment")
            # metadata remains empty []
    
    else:
        raise ValueError(
            f"❌ Unknown RIVA_DEPLOYMENT_TYPE: {deployment_type}\n"
            f"💡 Valid options: 'nvcf', 'self-hosted', 'cloud'"
        )
    
    # Create and return Auth object
    auth = riva.client.Auth(ssl_cert, use_ssl, riva_uri, metadata)
    logger.info("✅ Riva authentication configured successfully")
    
    return auth


def convert_to_wav(input_path: str, output_path: str) -> None:
    """Convert audio file to WAV format (mono, 16-bit, 22050Hz) using ffmpeg.
    
    Args:
        input_path: Path to input audio file (any format supported by ffmpeg)
        output_path: Path to output WAV file
    
    Raises:
        subprocess.CalledProcessError: If ffmpeg conversion fails
        FileNotFoundError: If ffmpeg is not installed
    """
    logger.info(f"Converting audio file: {input_path} -> {output_path}")
    
    # Verify input file exists
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    file_size = os.path.getsize(input_path)
    logger.info(f"Input file size: {file_size} bytes")
    
    cmd = [
        'ffmpeg',
        '-nostdin',          # Don't wait for user input
        '-hide_banner',      # Hide FFmpeg banner
        '-loglevel', 'error', # Only show errors
        '-i', input_path,
        '-ar', '22050',      # Sample rate: 22050 Hz
        '-ac', '1',          # Audio channels: 1 (mono)
        '-sample_fmt', 's16', # Sample format: signed 16-bit
        '-y',                # Overwrite output file without asking
        output_path
    ]
    
    logger.info(f"FFmpeg command: {' '.join(cmd)}")
    
    try:
        # Add timeout to prevent hanging forever (5 minutes max)
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minute timeout
        )
        logger.info("FFmpeg conversion completed successfully")
        
        # Verify output file was created
        if not os.path.exists(output_path):
            raise RuntimeError("FFmpeg completed but output file not created")
        
        output_size = os.path.getsize(output_path)
        logger.info(f"Output file size: {output_size} bytes")
        
        if result.stderr:
            logger.warning(f"FFmpeg warnings: {result.stderr}")
            
    except FileNotFoundError:
        logger.error("FFmpeg not found in system PATH")
        raise FileNotFoundError(
            "ffmpeg not found. Please install ffmpeg: sudo apt-get install ffmpeg"
        )
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg conversion timed out after 5 minutes")
        raise RuntimeError("FFmpeg conversion timed out - file may be too large or corrupted")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion failed with exit code {e.returncode}")
        logger.error(f"FFmpeg stderr: {e.stderr}")
        logger.error(f"FFmpeg stdout: {e.stdout}")
        raise RuntimeError(f"FFmpeg conversion failed: {e.stderr}")


def offline_transcribe(
    wav_path: str, 
    enable_diarization: bool = False, 
    max_speakers: int = 8,
    return_json: bool = False
) -> str | Dict[str, Any]:
    """Transcribe a WAV file using Riva offline recognition.

    Uses the same RecognitionConfig as in main.py's /v1/speech_recognition/transcribe.
    Returns the joined transcript across results.
    
    Args:
        wav_path: Path to the WAV file to transcribe
        enable_diarization: If True, enable speaker diarization
        max_speakers: Maximum number of speakers to identify (default: 8)
        return_json: If True, return structured data instead of plain text
    
    Returns:
        If return_json is False: plain text transcript
        If return_json is True: dictionary with structured transcript data
    """
    logger.info(f"Starting transcription for: {wav_path}")
    logger.info(f"Diarization: {enable_diarization}, Max speakers: {max_speakers}, JSON output: {return_json}")
    
    logger.info("Building authentication from environment...")
    auth = build_auth_from_env()
    
    logger.info("Creating ASR service...")
    asr_service = riva.client.ASRService(auth)

    logger.info("Configuring recognition settings...")
    config = riva.client.RecognitionConfig(
        language_code="en-US",
        max_alternatives=True,
        profanity_filter=False,
        enable_automatic_punctuation=False,
        verbatim_transcripts=False,
        enable_word_time_offsets=True,
    )
    
    # Add speaker diarization configuration if enabled
    if enable_diarization:
        logger.info(f"Adding speaker diarization config (max {max_speakers} speakers)...")
        riva.client.asr.add_speaker_diarization_to_config(
            config, 
            diarization_enable=True,
            diarization_max_speakers=max_speakers
        )

    logger.info("Reading audio file...")
    with open(wav_path, 'rb') as f:
        wav_bytes = f.read()
    logger.info(f"Audio file size: {len(wav_bytes)} bytes")

    logger.info("Preparing audio data for recognition...")
    data = io.BytesIO(wav_bytes).read()
    
    logger.info("Sending request to Riva ASR service (this may take a while)...")
    try:
        response = asr_service.offline_recognize(data, config)
        logger.info("Received response from Riva ASR service")
    except Exception as e:
        logger.error(f"ASR service failed: {e}", exc_info=True)
        raise
    
    # Print debug info (for troubleshooting)
    # riva.client.print_offline(response=response)

    # If JSON output is requested, build structured data
    if return_json:
        json_data = {
            "audio_file": wav_path,
            "diarization_enabled": enable_diarization,
            "max_speakers": max_speakers if enable_diarization else None,
            "segments": []
        }
        
        for res in response.results:
            if res.alternatives:
                alt = res.alternatives[0]
                segment_data = {
                    "transcript": alt.transcript,
                    "confidence": alt.confidence,
                    "words": []
                }
                
                if alt.words:
                    for word in alt.words:
                        word_data = {
                            "word": word.word,
                            "start_time": word.start_time / 1000.0,  # Convert ms to seconds
                            "end_time": word.end_time / 1000.0,
                            "confidence": word.confidence
                        }
                        speaker_tag = getattr(word, 'speaker_tag', None)
                        if speaker_tag is not None:
                            word_data["speaker"] = speaker_tag
                        segment_data["words"].append(word_data)
                
                json_data["segments"].append(segment_data)
        
        # Add a formatted transcript field
        if enable_diarization:
            formatted_lines = []
            for segment in json_data["segments"]:
                current_speaker = None
                current_segment = []
                
                for word_data in segment["words"]:
                    speaker = word_data.get("speaker")
                    if speaker is not None:
                        if current_speaker != speaker:
                            if current_segment:
                                formatted_lines.append({
                                    "speaker": current_speaker,
                                    "text": ' '.join(current_segment)
                                })
                            current_speaker = speaker
                            current_segment = [word_data["word"]]
                        else:
                            current_segment.append(word_data["word"])
                    else:
                        if current_speaker is not None and current_segment:
                            formatted_lines.append({
                                "speaker": current_speaker,
                                "text": ' '.join(current_segment)
                            })
                            current_speaker = None
                            current_segment = []
                        current_segment.append(word_data["word"])
                
                if current_segment:
                    formatted_lines.append({
                        "speaker": current_speaker,
                        "text": ' '.join(current_segment)
                    })
            
            json_data["formatted_transcript"] = formatted_lines
        else:
            json_data["formatted_transcript"] = [
                {"text": segment["transcript"]} 
                for segment in json_data["segments"]
            ]
        
        return json_data
    
    # Plain text output
    if enable_diarization:
        output_lines = []
        for res in response.results:
            if res.alternatives and res.alternatives[0].words:
                alt = res.alternatives[0]
                # Group consecutive words by speaker
                current_speaker = None
                current_segment = []
                
                for word in alt.words:
                    # Check if word has speaker_tag attribute
                    speaker_tag = getattr(word, 'speaker_tag', None)
                    
                    if speaker_tag is not None:
                        if current_speaker != speaker_tag:
                            # Speaker changed, output previous segment
                            if current_segment:
                                output_lines.append(f"[Speaker {current_speaker}]: {' '.join(current_segment)}")
                            current_speaker = speaker_tag
                            current_segment = [word.word]
                        else:
                            current_segment.append(word.word)
                    else:
                        # No speaker tag for this word
                        if current_speaker is not None and current_segment:
                            # Output previous segment with speaker
                            output_lines.append(f"[Speaker {current_speaker}]: {' '.join(current_segment)}")
                            current_speaker = None
                            current_segment = []
                        current_segment.append(word.word)
                
                # Output final segment for this result
                if current_segment:
                    if current_speaker is not None:
                        output_lines.append(f"[Speaker {current_speaker}]: {' '.join(current_segment)}")
                    else:
                        output_lines.append(' '.join(current_segment))
        
        return "\n".join(output_lines)
    else:
        # No diarization - return plain transcripts
        transcripts = []
        for res in response.results:
            if res.alternatives:
                transcripts.append(res.alternatives[0].transcript)
        return "\n".join(transcripts)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Transcribe a WAV file using NVIDIA Riva (offline)")
    parser.add_argument("audio_file", help="Path to audio file to transcribe")
    parser.add_argument("--convert", 
                        action="store_true",
                        help="Convert input file to WAV (mono, 16-bit, 22050Hz) using ffmpeg before transcription")
    parser.add_argument("--diarize", "--speaker-diarization", 
                        action="store_true",
                        dest="diarize",
                        help="Enable speaker diarization to identify different speakers")
    parser.add_argument("--max-speakers",
                        type=int,
                        default=8,
                        help="Maximum number of speakers to identify (default: 8, only used with --diarize)")
    parser.add_argument("--output", "-o",
                        help="Save transcription to JSON file (if not specified, prints to stdout)")
    args = parser.parse_args(argv)

    temp_file = None
    try:
        # Determine the file to transcribe
        if args.convert:
            # Create a temporary WAV file
            temp_fd, temp_file = tempfile.mkstemp(suffix='.wav', prefix='riva_converted_')
            os.close(temp_fd)  # Close the file descriptor, we just need the path
            
            print(f"Converting {args.audio_file} to WAV format...", file=sys.stderr)
            convert_to_wav(args.audio_file, temp_file)
            print(f"Conversion complete. Transcribing...", file=sys.stderr)
            wav_path = temp_file
        else:
            wav_path = args.audio_file
        
        # Transcribe
        result = offline_transcribe(
            wav_path, 
            enable_diarization=args.diarize,
            max_speakers=args.max_speakers,
            return_json=bool(args.output)
        )
        
        # Output result
        if args.output:
            # Save to JSON file
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"Transcription saved to {args.output}", file=sys.stderr)
        else:
            # Print to stdout
            print(result)
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        # Clean up temporary file if created
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception:
                pass  # Best effort cleanup


if __name__ == "__main__":
    raise SystemExit(main())



