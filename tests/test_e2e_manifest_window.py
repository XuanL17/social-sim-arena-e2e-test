from datetime import datetime, timezone
from ssa.questionnaire_api import open_rounds
now=datetime(2026,9,15,tzinfo=timezone.utc)
base={"round_id":"test","status":"open","lock_at":"2026-09-18T00:00:00Z","deadline":"2026-09-18T00:00:00Z"}
assert open_rounds({"rounds":[dict(base,published_at="2026-09-16T00:00:00Z")]},now)==[]
assert len(open_rounds({"rounds":[dict(base,published_at="2026-09-15T00:00:00Z")]},now))==1
assert open_rounds({"rounds":[base]},datetime(2026,9,18,tzinfo=timezone.utc))==[]
print("passed: publication boundary and deadline boundary")
