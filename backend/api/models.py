from django.db import models
from pydantic import BaseModel, Field
from typing import DefaultDict, List, Dict

# Model 1: For Coordinate data
class coordinates(BaseModel): 

    coord_x: int = Field(..., examples=1)
    coord_y: int = Field(..., examples=1)
    coord_z: int = Field(..., examples=1)

    