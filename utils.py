import logging
import os
import uuid

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"wav", "mp3", "m4a", "ogg"}

# MIME types for audio validation
ALLOWED_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/ogg",
    "application/ogg",
}


def allowed_file(filename: str) -> bool:
    """Check if filename has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_file_size(file_obj, max_size_bytes: int) -> bool:
    """
    Validate file size without reading entire file into memory.

    Args:
        file_obj: Werkzeug FileStorage object
        max_size_bytes: Maximum allowed size in bytes

    Returns:
        True if file is within size limit
    """
    # Seek to end to get file size
    file_obj.seek(0, os.SEEK_END)
    file_size = file_obj.tell()
    # Reset file pointer to beginning
    file_obj.seek(0)

    return file_size <= max_size_bytes


def validate_content_type(file_obj) -> bool:
    """
    Validate that the file has an allowed MIME type.

    Args:
        file_obj: Werkzeug FileStorage object

    Returns:
        True if content type is allowed
    """
    content_type = file_obj.content_type
    if not content_type:
        return False
    return content_type.lower() in ALLOWED_MIME_TYPES


def save_upload_securely(file_obj, upload_folder: str, max_size_bytes: int | None = None):
    """
    Saves a file with a unique UUID name to prevent overwrites.

    Args:
        file_obj: Werkzeug FileStorage object
        upload_folder: Directory to save the file
        max_size_bytes: Maximum file size (if None, uses config setting)

    Returns:
        Path to saved file

    Raises:
        ValueError: If file validation fails
    """
    if not file_obj or file_obj.filename == "":
        return None

    if not allowed_file(file_obj.filename):
        raise ValueError("File type not allowed. Supported formats: wav, mp3, m4a, ogg")

    # Validate content type
    if not validate_content_type(file_obj):
        raise ValueError(
            f"Invalid content type: {file_obj.content_type}. Must be an audio file."
        )

    # Get max size from config if not provided
    if max_size_bytes is None:
        from config import settings

        max_size_bytes = settings.max_upload_size_bytes

    # Validate file size
    if not validate_file_size(file_obj, max_size_bytes):
        max_mb = max_size_bytes / (1024 * 1024)
        raise ValueError(f"File too large. Maximum size is {max_mb:.0f}MB")

    # Generate unique name
    ext = file_obj.filename.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{ext}"

    # Create folder if not exists
    os.makedirs(upload_folder, exist_ok=True)

    save_path = os.path.join(upload_folder, unique_filename)
    file_obj.save(save_path)
    logger.info(f"File saved: {save_path}")
    return save_path


def validate_profile_data(form_data):
    """Ensures input data is valid and safe."""
    try:
        age = int(form_data.get("age", 0))
        if not (18 <= age <= 100):
            return None, "Возраст должен быть от 18 до 100 лет."

        gender = form_data.get("gender")
        if gender not in ["male", "female"]:
            return None, "Некорректный пол."

        smoking = form_data.get("smoking_status")
        if smoking not in ["smoker", "non-smoker"]:
            return None, "Некорректный статус курения."

        activity = form_data.get("activity_level")
        if activity not in ["sedentary", "moderate", "active"]:
            return None, "Некорректный уровень активности."

        return {
            "age": age,
            "gender": gender,
            "smoking_status": smoking,
            "activity_level": activity,
        }, None
    except ValueError:
        return None, "Ошибка формата данных."
