from pydantic import BaseModel, Field
from typing import List, Dict, Tuple, Set

class ScenaryDescription(BaseModel):
    description: str = Field(..., description="Scenary description by our Lumen Narrator", max_length=300)