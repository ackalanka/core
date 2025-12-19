# tests/unit/test_schemas.py
"""Unit tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError


class TestProfileModel:
    """Tests for ProfileModel validation."""

    def test_valid_profile(self):
        """Test valid profile data."""
        from schemas import ProfileModel

        profile = ProfileModel(
            age=45,
            gender="male",
            smoking_status="non-smoker",
            activity_level="moderate",
        )

        assert profile.age == 45
        assert profile.gender == "male"
        assert profile.smoking_status == "non-smoker"
        assert profile.activity_level == "moderate"

    def test_age_validation_min(self):
        """Test age minimum bound (18)."""
        from schemas import ProfileModel

        with pytest.raises(ValidationError):
            ProfileModel(
                age=17,
                gender="male",
                smoking_status="non-smoker",
                activity_level="moderate",
            )

    def test_age_validation_max(self):
        """Test age maximum bound (100)."""
        from schemas import ProfileModel

        with pytest.raises(ValidationError):
            ProfileModel(
                age=101,
                gender="male",
                smoking_status="non-smoker",
                activity_level="moderate",
            )

    def test_invalid_gender(self):
        """Test invalid gender value."""
        from schemas import ProfileModel

        with pytest.raises(ValidationError):
            ProfileModel(
                age=45,
                gender="invalid",
                smoking_status="non-smoker",
                activity_level="moderate",
            )

    def test_valid_genders(self):
        """Test all valid gender options."""
        from schemas import ProfileModel

        for gender in ["male", "female"]:
            profile = ProfileModel(
                age=45,
                gender=gender,
                smoking_status="non-smoker",
                activity_level="moderate",
            )
            assert profile.gender == gender

    def test_valid_smoking_statuses(self):
        """Test all valid smoking status options."""
        from schemas import ProfileModel

        # Actual values in schema: "smoker", "non-smoker"
        for status in ["smoker", "non-smoker"]:
            profile = ProfileModel(
                age=45, gender="male", smoking_status=status, activity_level="moderate"
            )
            assert profile.smoking_status == status

    def test_valid_activity_levels(self):
        """Test all valid activity level options."""
        from schemas import ProfileModel

        # Actual values in schema: "sedentary", "moderate", "active"
        for level in ["sedentary", "moderate", "active"]:
            profile = ProfileModel(
                age=45, gender="male", smoking_status="non-smoker", activity_level=level
            )
            assert profile.activity_level == level


class TestUserModels:
    """Tests for user authentication models."""

    def test_valid_register(self):
        """Test valid registration data."""
        from schemas import UserRegisterModel

        user = UserRegisterModel(email="test@example.com", password="SecurePass123")

        assert user.email == "test@example.com"
        assert user.password == "SecurePass123"

    def test_invalid_email(self):
        """Test invalid email format."""
        from schemas import UserRegisterModel

        with pytest.raises(ValidationError):
            UserRegisterModel(email="not-an-email", password="SecurePass123")

    def test_short_password(self):
        """Test password minimum length."""
        from schemas import UserRegisterModel

        with pytest.raises(ValidationError):
            UserRegisterModel(email="test@example.com", password="short")

    def test_valid_login(self):
        """Test valid login data."""
        from schemas import UserLoginModel

        login = UserLoginModel(email="test@example.com", password="SecurePass123")

        assert login.email == "test@example.com"
