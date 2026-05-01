from typing import List, Optional
from pydantic import BaseModel


class RankingEntry(BaseModel):
    user_id: str
    name: str
    email: str
    total_net: float
    count: int
    fast_count: int
    avg_elapsed_min: int
    badge: str  # "gold" | "silver" | "bronze" | ""
    is_me: bool = False


class RankingOut(BaseModel):
    period: str
    top_earners: List[RankingEntry]
    top_fast: List[RankingEntry]
    me_earners_pos: Optional[int] = None
    me_fast_pos: Optional[int] = None
