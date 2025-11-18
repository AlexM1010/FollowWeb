"""
URL reconstruction helpers for Freesound metadata.

These functions reconstruct full URLs from optimized base paths stored in metadata.
This allows us to store 1 base path instead of 4-8 full URLs, reducing storage by ~38%.
"""

from typing import Optional


def get_preview_url(
    metadata: dict, quality: str = "hq", format: str = "mp3"
) -> Optional[str]:
    """
    Get preview URL from metadata.

    Args:
        metadata: Sample metadata dict
        quality: "hq" or "lq" (default: "hq")
        format: "mp3" or "ogg" (default: "mp3")

    Returns:
        Full preview URL or None if not available

    Examples:
        >>> get_preview_url(metadata)  # Returns HQ MP3
        'https://cdn.freesound.org/previews/0/406_196-hq.mp3'

        >>> get_preview_url(metadata, quality="lq", format="ogg")
        'https://cdn.freesound.org/previews/0/406_196-lq.ogg'
    """
    # Try optimized storage first (new format)
    if "preview_base" in metadata:
        base = metadata["preview_base"]
        return f"https://cdn.freesound.org/{base}-{quality}.{format}"

    # Fallback to old format (full previews dict)
    if "previews" in metadata and isinstance(metadata["previews"], dict):
        key = f"preview_{quality}_{format}"
        return metadata["previews"].get(key)

    # Fallback to audio_url (legacy)
    if "audio_url" in metadata:
        return metadata["audio_url"]

    return None


def get_all_preview_urls(metadata: dict) -> dict[str, str]:
    """
    Get all preview URLs from metadata.

    Args:
        metadata: Sample metadata dict

    Returns:
        Dictionary with all preview URLs

    Example:
        >>> get_all_preview_urls(metadata)
        {
            'preview_hq_mp3': 'https://cdn.freesound.org/previews/0/406_196-hq.mp3',
            'preview_hq_ogg': 'https://cdn.freesound.org/previews/0/406_196-hq.ogg',
            'preview_lq_mp3': 'https://cdn.freesound.org/previews/0/406_196-lq.mp3',
            'preview_lq_ogg': 'https://cdn.freesound.org/previews/0/406_196-lq.ogg'
        }
    """
    # Try optimized storage first (new format)
    if "preview_base" in metadata:
        base = f"https://cdn.freesound.org/{metadata['preview_base']}"
        return {
            "preview_hq_mp3": f"{base}-hq.mp3",
            "preview_hq_ogg": f"{base}-hq.ogg",
            "preview_lq_mp3": f"{base}-lq.mp3",
            "preview_lq_ogg": f"{base}-lq.ogg",
        }

    # Fallback to old format
    if "previews" in metadata and isinstance(metadata["previews"], dict):
        return metadata["previews"]

    return {}


def get_image_url(
    metadata: dict, image_type: str = "waveform", size: str = "m", bw: bool = False
) -> Optional[str]:
    """
    Get image URL from metadata.

    Args:
        metadata: Sample metadata dict
        image_type: "waveform" or "spectral" (default: "waveform")
        size: "m" (medium) or "l" (large) (default: "m")
        bw: Black & white version (default: False)

    Returns:
        Full image URL or None if not available

    Examples:
        >>> get_image_url(metadata)  # Returns medium waveform
        'https://cdn.freesound.org/displays/0/406_196_wave_M.png'

        >>> get_image_url(metadata, image_type="spectral", size="l", bw=True)
        'https://cdn.freesound.org/displays/0/406_196_spec_bw_L.jpg'
    """
    # Try optimized storage first (new format)
    if "image_base" in metadata:
        base = f"https://cdn.freesound.org/{metadata['image_base']}"

        # Determine file extension
        ext = "jpg" if image_type == "spectral" else "png"

        # Build image type string
        type_str = "spec" if image_type == "spectral" else "wave"
        if bw:
            type_str += "_bw"

        return f"{base}_{type_str}_{size.upper()}.{ext}"

    # Fallback to old format (full images dict)
    if "images" in metadata and isinstance(metadata["images"], dict):
        key = f"{image_type}"
        if bw:
            key += "_bw"
        key += f"_{size}"
        return metadata["images"].get(key)

    return None


def get_all_image_urls(metadata: dict) -> dict[str, str]:
    """
    Get all image URLs from metadata.

    Args:
        metadata: Sample metadata dict

    Returns:
        Dictionary with all image URLs

    Example:
        >>> get_all_image_urls(metadata)
        {
            'waveform_m': 'https://cdn.freesound.org/displays/0/406_196_wave_M.png',
            'waveform_l': 'https://cdn.freesound.org/displays/0/406_196_wave_L.png',
            ...
        }
    """
    # Try optimized storage first (new format)
    if "image_base" in metadata:
        base = f"https://cdn.freesound.org/{metadata['image_base']}"
        return {
            "waveform_m": f"{base}_wave_M.png",
            "waveform_l": f"{base}_wave_L.png",
            "spectral_m": f"{base}_spec_M.jpg",
            "spectral_l": f"{base}_spec_L.jpg",
            "waveform_bw_m": f"{base}_wave_bw_M.png",
            "waveform_bw_l": f"{base}_wave_bw_L.png",
            "spectral_bw_m": f"{base}_spec_bw_M.jpg",
            "spectral_bw_l": f"{base}_spec_bw_L.jpg",
        }

    # Fallback to old format
    if "images" in metadata and isinstance(metadata["images"], dict):
        return metadata["images"]

    return {}
