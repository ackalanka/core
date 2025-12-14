from pydantic import BaseModel, Field
from typing import Literal

class ProfileModel(BaseModel):
    age: int = Field(..., ge=18, le=100)
    gender: Literal["male", "female"]
    smoking_status: Literal["smoker", "non-smoker"]
    activity_level: Literal["sedentary", "moderate", "active"]
