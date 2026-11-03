"""Observer: subscribers react to TripCreated without hard-coding them in the publisher."""
from collections.abc import Iterable
from typing import Protocol
import sqlite3

class TripCreatedObserver(Protocol):
    def on_trip_created(self, db: sqlite3.Connection, event: dict) -> None: ...

class NotificationObserver:
    """Original notification behavior, moved unchanged out of TripsRepository."""
    def on_trip_created(self, db: sqlite3.Connection, event: dict) -> None:
        db.execute(
            'INSERT OR IGNORE INTO notification_inbox (event_id, trip_id, message) VALUES (?, ?, ?)',
            (event['event_id'], event['data']['id'], 'Заплановано рейс ' + event['data']['id'])
        )

class TripEventPublisher:
    def __init__(self, subscribers: Iterable[TripCreatedObserver] | None = None):
        self.subscribers = list(subscribers) if subscribers is not None else [NotificationObserver()]

    def publish(self, db: sqlite3.Connection, event: dict) -> None:
        for subscriber in self.subscribers:
            subscriber.on_trip_created(db, event)
