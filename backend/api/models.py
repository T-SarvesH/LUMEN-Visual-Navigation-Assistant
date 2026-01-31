from django.db import models
from pydantic import BaseModel, Field
from typing import DefaultDict, List, Dict

# Model 1: For Coordinate data

class UserState(BaseModel):
    description_interval: int = Field(10, description="Scenary description interval for the narrator")
    speech_language: str = Field("English", description="TTS Language for the Narrator")