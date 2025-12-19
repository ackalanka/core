# tests/unit/test_utils.py
"""Unit tests for utility functions."""
import io

from werkzeug.datastructures import FileStorage


class TestAllowedFile:
    """Tests for allowed_file function."""

    def test_allowed_extensions(self):
        """Test valid audio file extensions."""
        from utils import allowed_file

        # Actual allowed: wav, mp3, m4a, ogg
        valid_files = ["audio.wav", "audio.mp3", "audio.m4a", "audio.ogg"]
        for filename in valid_files:
            assert allowed_file(filename) is True

    def test_disallowed_extensions(self):
        """Test invalid file extensions."""
        from utils import allowed_file

        invalid_files = ["file.txt", "file.exe", "file.py", "file.doc", "file.flac"]
        for filename in invalid_files:
            assert allowed_file(filename) is False

    def test_no_extension(self):
        """Test file without extension."""
        from utils import allowed_file

        assert allowed_file("filename") is False

    def test_case_insensitive(self):
        """Test case-insensitive extension matching."""
        from utils import allowed_file

        assert allowed_file("audio.WAV") is True
        assert allowed_file("audio.Mp3") is True


class TestValidateFileSize:
    """Tests for file size validation."""

    def test_valid_file_size(self):
        """Test file within size limit."""
        from utils import validate_file_size

        # 1MB file (under 10MB limit)
        file_data = io.BytesIO(b"x" * (1024 * 1024))
        file = FileStorage(stream=file_data, filename="test.wav")

        # Returns True if within limit
        result = validate_file_size(file, max_size_bytes=10 * 1024 * 1024)
        assert result is True

    def test_file_too_large(self):
        """Test file exceeding size limit."""
        from utils import validate_file_size

        # 2MB file (over 1MB limit)
        file_data = io.BytesIO(b"x" * (2 * 1024 * 1024))
        file = FileStorage(stream=file_data, filename="test.wav")

        # Returns False if over limit
        result = validate_file_size(file, max_size_bytes=1 * 1024 * 1024)
        assert result is False


class TestValidateContentType:
    """Tests for content type validation."""

    def test_valid_audio_types(self):
        """Test valid audio MIME types."""
        from utils import validate_content_type

        valid_types = [
            "audio/wav",
            "audio/mpeg",
            "audio/mp3",
            "audio/ogg",
            "audio/x-wav",
        ]

        for content_type in valid_types:
            file_data = io.BytesIO(b"test data")
            file = FileStorage(
                stream=file_data, filename="test.wav", content_type=content_type
            )
            # Returns True for valid types
            assert validate_content_type(file) is True

    def test_invalid_content_type(self):
        """Test invalid content types."""
        from utils import validate_content_type

        file_data = io.BytesIO(b"test data")
        file = FileStorage(
            stream=file_data, filename="test.txt", content_type="text/plain"
        )

        # Returns False for invalid types
        assert validate_content_type(file) is False
