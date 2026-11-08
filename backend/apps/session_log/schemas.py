from ninja import Schema


class LogEntryOut(Schema):
    id: int
    session: int
    kind: str
    author: str
    author_id: str | None
    is_ai: bool
    summary: str
    data: dict
    created_at: str


class LogActorOut(Schema):
    id: str | None
    label: str
    is_ai: bool


class LogSessionOut(Schema):
    session: int
    started_at: str
    ended_at: str
    entries: int
    actors: list[LogActorOut]
