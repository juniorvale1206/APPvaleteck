from typing import List
from pydantic import BaseModel


class GamificationOut(BaseModel):
    level: dict
    achievements: List[dict]
    weekly_history: List[dict]
    total_xp: int
    unlocked_count: int
    achievements_total: int
