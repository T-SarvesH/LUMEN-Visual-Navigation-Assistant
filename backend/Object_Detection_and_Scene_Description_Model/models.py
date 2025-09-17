from django.db import models
from pydantic import BaseModel, Field
from typing import List, Dict, DefaultDict

#Model 1: For the YOLO Data
class Yolo_Model_Output(BaseModel):

    xyxy: List[float] = Field(..., examples=[100.5, 200.5, 200.5, 200.8])
    conf: float = Field(..., examples=0.85)
    objClass: str = Field(..., examples="bicycle")
    classIndex: int = Field(..., examples=0, ge=0)