"""
# ArangoWAL

Subscribe to Write-Ahead-Log changes on an ArangoDB database.
"""

import json
import logging
import signal
import sys
import time
from sched import scheduler
from threading import Timer
from typing import Callable

from arango import ArangoClient
from arango.database import StandardDatabase
from pyee.base import EventEmitter, Handler

__version__ = "0.1.0"
__all__ = ["ArangoWAL", "OPERATIONS", "POLLING_INTERVAL_SECS"]

POLLING_INTERVAL_SECS = 1

OPERATIONS = {
    1100: "create_database",
    1101: "drop_database",
    2000: "create_collection",
    2001: "drop_collection",
    2002: "rename_collection",
    2003: "change_collection",
    2004: "truncate_collection",
    2100: "create_index",
    2101: "drop_index",
    2110: "create_view",
    2111: "drop_view",
    2112: "change_view",
    2200: "start_transaction",
    2201: "commit_transaction",
    2202: "abort_transaction",
    2300: "insert_replace_document",
    2302: "remove_document",
}


class ArangoWAL(EventEmitter):
    """ArangoWAL allows subscribing to ArangoDB WAL events."""

    def __init__(self, host: str, polling_interval: int = POLLING_INTERVAL_SECS):
        self.polling_interval = polling_interval
        self.logger = logging.getLogger(__name__)
        self._client = ArangoClient(host)
        self._timer = None
        self._running = False
        self._wal = None
        signal.signal(signal.SIGINT, self._exit_gracefully)
        signal.signal(signal.SIGTERM, self._exit_gracefully)
        super().__init__()

    def connect(self, **kwargs) -> StandardDatabase:
        """Connect to an ArangoDB database."""
        self._wal = self._client.db(**kwargs).wal

    def subscribe(self, event: str, handler: Handler) -> Handler:
        """Subscribe to an event."""
        self.logger.info("subscribing to event")
        self.add_listener(event, handler)
        return self

    def unsubscribe(self, event: str, handler: Callable) -> None:
        """Unsubscribe to an event."""
        self.logger.info("unsubscribing from event")
        self.remove_listener(event, handler)
        return self

    def start(self):
        """Start listening for changes."""
        self.logger.info("start listening")
        self._running = True
        self._pool_wal()
        return self

    def _pool_wal(self, last_tick: int = 0):
        self.logger.info("called _poll_wal")
        if not self._running:
            return
        tick = self._extract_last_tick(last_tick)
        if tick:
            col, event, data = ArangoWAL.extract(tick)
            if col:
                self.logger.debug("emitting to %s with %s: %s", col, event, data)
                self.emit(col, event, data)
            last_tick = tick["tick"]
        self._timer = Timer(self.polling_interval, self._pool_wal, args=[last_tick])
        self._timer.start()

    def _extract_last_tick(self, last_tick: int):
        self.logger.debug("last tick: %s", last_tick)
        ticks = self._wal.tail(lower=last_tick)["content"].split("\n")
        last_tick = ticks[-2:][:-1]
        return json.loads(last_tick[0]) if last_tick else None

    def stop(self):
        """Stop listening for changes."""
        self.logger.info("stopping")
        self._running = False
        if self._timer:
            self._timer.cancel()
        return self

    @staticmethod
    def extract(tick):
        """Extract information from tick."""
        data = tick.get("data", None)
        operation = OPERATIONS.get(tick.get("type", ""), "unknown_operation")
        collection = data["_id"].split("/")[0] if data else None
        return collection, operation, data

    def _exit_gracefully(self, _signum, _stackframe):
        self.stop()
        sys.exit(0)
