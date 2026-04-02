# models/log_schema.py
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional

class RequestLog(BaseModel):
    request_id:       str                        # uuid — trace individual requests
    user_id:          int
    user_name:        str
    method:           str                        # GET, POST, etc.
    path:             str                        # /services/users/1
    status_code:      int
    latency_ms:       float                      # end-to-end gateway latency
    upstream_service: Optional[str] = None       # which backend was hit
    cache_hit:        bool = False               # for caching feature later
    timestamp:        datetime = Field(
                          default_factory=lambda: datetime.now(timezone.utc)
                      )

    def to_dict(self) -> dict:
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data