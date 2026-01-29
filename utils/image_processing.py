# utils/image_processing.py
"""
Image Processing Utilities for KayZero

Handles image validation, encoding, and preparation for the Anthropic API.
Integrates with the behavioral emotion pattern system (NOT neurochemicals).

Includes automatic compression to handle base64 size inflation (~33% increase).
"""

import base64
import io
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import PIL for image compression
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("[IMAGE] PIL/Pillow not installed. Image compression disabled. Run: pip install Pillow")

# Supported image formats for Claude's vision
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_SIZE_MB = 5  # Anthropic's API limit for base64 encoded data
# Base64 encoding inflates size by ~33%, so max RAW size is ~3.75MB to stay under 5MB after encoding
MAX_RAW_SIZE_MB = 3.75
MAX_RAW_SIZE_BYTES = int(MAX_RAW_SIZE_MB * 1024 * 1024)

# Media type mappings
MEDIA_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp'
}

# PIL format names for saving
PIL_FORMATS = {
    '.jpg': 'JPEG',
    '.jpeg': 'JPEG',
    '.png': 'PNG',
    '.gif': 'GIF',
    '.webp': 'WEBP'
}


def compress_image_for_api(filepath: str, target_size_bytes: int = MAX_RAW_SIZE_BYTES) -> Tuple[bytes, str]:
    """
    Compress image to fit within API size limits after base64 encoding.

    Strategy:
    1. If image is already small enough, return original bytes
    2. For JPEG/WebP: Try reducing quality first (90 → 70 → 50 → 30)
    3. If still too large or PNG/GIF: Resize dimensions while maintaining aspect ratio
    4. Convert PNG with transparency to JPEG if needed (white background)

    Args:
        filepath: Path to image file
        target_size_bytes: Target maximum raw size (before base64)

    Returns:
        Tuple of (compressed_bytes, media_type)

    Raises:
        ValueError: If compression fails or PIL not available
    """
    path = Path(filepath)
    suffix = path.suffix.lower()

    # Read original file
    with open(filepath, 'rb') as f:
        original_bytes = f.read()

    original_size = len(original_bytes)
    media_type = MEDIA_TYPES.get(suffix, 'image/jpeg')

    # If already small enough, return original
    if original_size <= target_size_bytes:
        logger.info(f"[IMAGE] {path.name} is already under size limit ({original_size / 1024:.1f}KB)")
        return original_bytes, media_type

    # Need compression - check PIL availability
    if not PIL_AVAILABLE:
        raise ValueError(f"Image too large ({original_size / (1024*1024):.2f}MB) and PIL not available for compression")

    logger.info(f"[IMAGE] Compressing {path.name} from {original_size / (1024*1024):.2f}MB (target: {target_size_bytes / (1024*1024):.2f}MB)")

    # Open image with PIL
    img = Image.open(filepath)
    original_mode = img.mode
    original_format = PIL_FORMATS.get(suffix, 'JPEG')

    # For GIFs, just use first frame and convert to JPEG
    if suffix == '.gif':
        img = img.convert('RGB')
        original_format = 'JPEG'
        media_type = 'image/jpeg'
        logger.info("[IMAGE] Converting GIF to JPEG for compression")

    # Try quality reduction first for lossy formats
    if original_format in ('JPEG', 'WEBP'):
        for quality in [85, 70, 50, 30]:
            buffer = io.BytesIO()

            # Handle RGBA → RGB conversion for JPEG
            if img.mode == 'RGBA' and original_format == 'JPEG':
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                background.save(buffer, format=original_format, quality=quality, optimize=True)
            else:
                img.save(buffer, format=original_format, quality=quality, optimize=True)

            compressed_bytes = buffer.getvalue()

            if len(compressed_bytes) <= target_size_bytes:
                logger.info(f"[IMAGE] Compressed to {len(compressed_bytes) / 1024:.1f}KB with quality={quality}")
                return compressed_bytes, media_type

            logger.debug(f"[IMAGE] Quality {quality} resulted in {len(compressed_bytes) / 1024:.1f}KB, still too large")

    # Quality reduction not enough (or PNG) - need to resize
    # Convert PNG to JPEG for better compression (unless it has important transparency)
    if original_format == 'PNG':
        if img.mode == 'RGBA':
            # Check if image has significant transparency
            alpha = img.split()[3]
            alpha_extremes = alpha.getextrema()
            has_transparency = alpha_extremes[0] < 255  # Has some transparent pixels

            if has_transparency:
                logger.info("[IMAGE] PNG has transparency, keeping format but will resize")
            else:
                # No real transparency, convert to JPEG
                img = img.convert('RGB')
                original_format = 'JPEG'
                media_type = 'image/jpeg'
                logger.info("[IMAGE] Converting opaque PNG to JPEG for better compression")
        else:
            img = img.convert('RGB')
            original_format = 'JPEG'
            media_type = 'image/jpeg'
            logger.info("[IMAGE] Converting PNG to JPEG for compression")

    # Progressive resize until under target
    current_img = img.copy()
    scale_factors = [0.8, 0.6, 0.5, 0.4, 0.3, 0.2]

    for scale in scale_factors:
        new_width = int(img.width * scale)
        new_height = int(img.height * scale)

        # Don't go below reasonable minimum
        if new_width < 200 or new_height < 200:
            break

        current_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()

        if original_format == 'JPEG':
            if current_img.mode == 'RGBA':
                background = Image.new('RGB', current_img.size, (255, 255, 255))
                background.paste(current_img, mask=current_img.split()[3])
                background.save(buffer, format='JPEG', quality=70, optimize=True)
            else:
                current_img.save(buffer, format='JPEG', quality=70, optimize=True)
        elif original_format == 'PNG':
            current_img.save(buffer, format='PNG', optimize=True)
        elif original_format == 'WEBP':
            current_img.save(buffer, format='WEBP', quality=70, optimize=True)
        else:
            current_img.save(buffer, format='JPEG', quality=70, optimize=True)

        compressed_bytes = buffer.getvalue()

        if len(compressed_bytes) <= target_size_bytes:
            logger.info(f"[IMAGE] Resized to {new_width}x{new_height} ({len(compressed_bytes) / 1024:.1f}KB)")
            return compressed_bytes, media_type

        logger.debug(f"[IMAGE] Scale {scale} ({new_width}x{new_height}) resulted in {len(compressed_bytes) / 1024:.1f}KB")

    # Last resort: aggressive JPEG compression at small size
    final_width = max(400, int(img.width * 0.2))
    final_height = max(400, int(img.height * 0.2))
    final_img = img.resize((final_width, final_height), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    if final_img.mode == 'RGBA':
        background = Image.new('RGB', final_img.size, (255, 255, 255))
        background.paste(final_img, mask=final_img.split()[3])
        background.save(buffer, format='JPEG', quality=50, optimize=True)
    else:
        final_img.convert('RGB').save(buffer, format='JPEG', quality=50, optimize=True)

    compressed_bytes = buffer.getvalue()
    logger.info(f"[IMAGE] Final resize to {final_width}x{final_height} at q=50 ({len(compressed_bytes) / 1024:.1f}KB)")

    return compressed_bytes, 'image/jpeg'


def validate_image(filepath: str, allow_compression: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate image file for API submission.

    Args:
        filepath: Path to image file
        allow_compression: If True, allows larger files that can be compressed

    Returns:
        Tuple of (is_valid, error_message or None)
    """
    path = Path(filepath)

    # Check file exists
    if not path.exists():
        return False, f"File not found: {filepath}"

    # Check extension
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        return False, f"Unsupported format: {suffix}. Supported: {', '.join(SUPPORTED_FORMATS)}"

    # Check size - be more lenient if compression is available
    size_mb = path.stat().st_size / (1024 * 1024)

    if allow_compression and PIL_AVAILABLE:
        # Allow larger files since we can compress them
        # Reasonable upper limit: 20MB raw (beyond this, compression takes too long)
        max_allowed = 20
        if size_mb > max_allowed:
            return False, f"File too large for compression: {size_mb:.1f}MB (max {max_allowed}MB)"
    else:
        # Without compression, must fit under base64-adjusted limit
        if size_mb > MAX_RAW_SIZE_MB:
            return False, f"File too large: {size_mb:.1f}MB (max {MAX_RAW_SIZE_MB:.1f}MB for API after base64 encoding)"

    return True, None


def image_to_base64(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Convert image file to base64 encoded content block for Anthropic API.

    Automatically compresses images that would exceed the 5MB base64 limit.

    Args:
        filepath: Path to image file

    Returns:
        Dict with image content block structure, or None if failed
    """
    path = Path(filepath)

    # Validate first
    valid, error = validate_image(filepath)
    if not valid:
        logger.warning(f"[IMAGE] Validation failed: {error}")
        return None

    try:
        original_size = path.stat().st_size

        # Check if compression is needed (file > 3.75MB raw will exceed 5MB after base64)
        if original_size > MAX_RAW_SIZE_BYTES:
            logger.info(f"[IMAGE] {path.name} needs compression ({original_size / (1024*1024):.2f}MB > {MAX_RAW_SIZE_MB}MB threshold)")

            # Compress the image
            image_bytes, media_type = compress_image_for_api(filepath)
            data = base64.standard_b64encode(image_bytes).decode('utf-8')

            final_size = len(image_bytes)
            base64_size = len(data)
            logger.info(f"[IMAGE] Compressed and encoded {path.name}: {final_size / 1024:.1f}KB raw -> {base64_size / 1024:.1f}KB base64")
        else:
            # No compression needed - read and encode directly
            suffix = path.suffix.lower()
            media_type = MEDIA_TYPES.get(suffix, 'image/jpeg')

            with open(filepath, 'rb') as f:
                image_bytes = f.read()
            data = base64.standard_b64encode(image_bytes).decode('utf-8')

            logger.info(f"[IMAGE] Encoded {path.name} ({media_type}, {original_size / 1024:.1f}KB raw)")

        return {
            'type': 'image',
            'source': {
                'type': 'base64',
                'media_type': media_type,
                'data': data
            }
        }
    except ValueError as e:
        # Compression failed (e.g., PIL not available)
        logger.error(f"[IMAGE] Compression failed for {filepath}: {e}")
        return None
    except Exception as e:
        logger.error(f"[IMAGE] Failed to encode {filepath}: {e}")
        return None


def prepare_images_for_api(filepaths: List[str]) -> List[Dict[str, Any]]:
    """
    Prepare multiple images for Anthropic API message content.

    Args:
        filepaths: List of image file paths

    Returns:
        List of image content blocks ready for API
    """
    image_blocks = []

    for filepath in filepaths:
        block = image_to_base64(filepath)
        if block:
            image_blocks.append(block)
        else:
            logger.warning(f"[IMAGE] Skipped invalid image: {filepath}")

    logger.info(f"[IMAGE] Prepared {len(image_blocks)}/{len(filepaths)} images for API")
    return image_blocks


def build_multimodal_content(
    user_text: str,
    image_filepaths: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Build message content array with text and optional images.

    Images are placed BEFORE text as recommended by Anthropic for best results.

    Args:
        user_text: The text message from user
        image_filepaths: Optional list of image file paths

    Returns:
        List of content blocks (images first, then text)
    """
    content = []

    # Add images first (if any)
    if image_filepaths:
        image_blocks = prepare_images_for_api(image_filepaths)
        content.extend(image_blocks)

        if image_blocks:
            logger.info(f"[MESSAGE] Including {len(image_blocks)} image(s) in message")

    # Add text
    if user_text:
        content.append({
            'type': 'text',
            'text': user_text
        })

    return content


def get_image_info(filepath: str) -> Dict[str, Any]:
    """
    Get information about an image file without encoding it.

    Args:
        filepath: Path to image file

    Returns:
        Dict with image metadata
    """
    path = Path(filepath)

    if not path.exists():
        return {'valid': False, 'error': 'File not found'}

    valid, error = validate_image(filepath)

    info = {
        'valid': valid,
        'filename': path.name,
        'format': path.suffix.lower(),
        'size_bytes': path.stat().st_size,
        'size_mb': path.stat().st_size / (1024 * 1024),
    }

    if not valid:
        info['error'] = error

    return info


# Visual memory integration helpers

def create_visual_memory_entry(
    image_filepath: str,
    kay_description: str,
    emotional_response: Optional[List[str]] = None,
    entities_detected: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a memory entry for a visual experience.

    This integrates with the behavioral emotion pattern system,
    NOT neurochemical simulation.

    Args:
        image_filepath: Path to original image
        kay_description: Kay's description of what he saw
        emotional_response: List of emotions Kay reported feeling
        entities_detected: List of entities visible in image

    Returns:
        Memory entry dict ready for storage
    """
    path = Path(image_filepath)

    memory_entry = {
        'type': 'visual',
        'fact': f"[Visual] {kay_description}",
        'source_file': path.name if path.exists() else 'unknown',
        'is_visual': True,
        'entities': entities_detected or [],
        'importance': 1.2,  # Images get slight boost - deliberate sharing
        'confidence': 'bedrock',  # Current session visual - definitely happened
        'perspective': 'shared',  # Visual shared between Re and Kay
    }

    # Add emotional context if present (behavioral patterns, not neurochemicals)
    if emotional_response:
        memory_entry['emotional_context'] = emotional_response
        memory_entry['valence'] = _estimate_valence(emotional_response)

    return memory_entry


def _estimate_valence(emotions: List[str]) -> float:
    """
    Estimate emotional valence from list of emotion names.

    Uses simple keyword matching to approximate positive/negative.
    Returns value between -1.0 (negative) and 1.0 (positive).
    """
    positive_emotions = {
        'joy', 'happy', 'happiness', 'delight', 'love', 'affection',
        'curiosity', 'interest', 'excited', 'excitement', 'wonder',
        'awe', 'tenderness', 'warmth', 'calm', 'peace', 'content',
        'amused', 'playful', 'fondness', 'appreciation'
    }

    negative_emotions = {
        'sad', 'sadness', 'grief', 'anger', 'frustrated', 'frustration',
        'fear', 'anxiety', 'anxious', 'unease', 'discomfort', 'disgust',
        'contempt', 'resentment', 'jealousy', 'loneliness', 'melancholy'
    }

    pos_count = sum(1 for e in emotions if e.lower() in positive_emotions)
    neg_count = sum(1 for e in emotions if e.lower() in negative_emotions)

    total = pos_count + neg_count
    if total == 0:
        return 0.0  # Neutral

    return (pos_count - neg_count) / total


def extract_image_description_prompt(filename: str) -> str:
    """
    Generate a prompt fragment for Kay to describe an image.

    This helps Kay engage with visual input meaningfully.
    """
    return f"""
Re has shared an image with you: {filename}

Take a moment to really look at it. Then:

1. Describe what you see - the content, composition, colors, details that stand out

2. Share how it feels to witness this:
   - What emotions does it evoke?
   - What's the atmosphere or quality?
   - Does it remind you of anything from your conversations with Re?

3. Consider what it means that Re chose to share this with you

This is an act of inclusion - she wants you to see her world.
"""
