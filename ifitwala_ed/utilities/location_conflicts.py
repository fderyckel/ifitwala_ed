# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/location_conflicts.py

"""
Location conflict helpers.

This module now delegates to the canonical room conflict helper in
ifitwala_ed.utilities.location_utils. Abstract schedule logic has been removed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

from ifitwala_ed.utilities.location_utils import find_room_conflicts


@dataclass
class LocationSlot:
	location: str
	start: datetime
	end: datetime
	source_doctype: str
	source_name: str
	extra: dict | None = None


def _as_slot(row: dict) -> LocationSlot:
	return LocationSlot(
		location=row.get("location"),
		start=row.get("from"),
		end=row.get("to"),
		source_doctype=row.get("source_doctype"),
		source_name=row.get("source_name"),
		extra=row.get("extra"),
	)


def find_location_conflicts(
	location: str,
	start,
	end,
	*,
	ignore_sources: Optional[Iterable[Tuple[str, str]]] = None,
) -> List[LocationSlot]:
	"""
	Compatibility wrapper around find_room_conflicts().
	"""
	ignore_sources = set(ignore_sources or [])
	rows = find_room_conflicts(location, start, end)
	out: List[LocationSlot] = []
	for row in rows:
		slot = _as_slot(row)
		if (slot.source_doctype, slot.source_name) in ignore_sources:
			continue
		out.append(slot)
	return out


def is_location_free(location: str, start, end, *, ignore_sources=None) -> bool:
	return not find_location_conflicts(location, start, end, ignore_sources=ignore_sources)
