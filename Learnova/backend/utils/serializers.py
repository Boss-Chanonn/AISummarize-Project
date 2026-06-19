from datetime import datetime, timezone
from typing import Any, Iterable


def _to_iso_utc(value: datetime) -> str:
    """Serialize datetimes as explicit UTC to avoid client-side timezone drift."""
    dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def serialize_mongo_doc(
    doc: dict[str, Any],
    *,
    datetime_fields: set[str] | None = None,
    drop_fields: set[str] | None = None,
) -> dict[str, Any]:
    """Convert MongoDB documents into JSON-friendly dictionaries.

    Args:
        doc: MongoDB document to serialize.
        datetime_fields: Optional set of datetime fields to convert to ISO strings.
            If not provided, all top-level datetime values are converted.
        drop_fields: Optional set of fields to remove from output.

    Returns:
        A dictionary safe to return from API responses.
    """
    out = dict(doc)

    if "_id" in out:
        out["_id"] = str(out["_id"])

    if drop_fields:
        for field in drop_fields:
            out.pop(field, None)

    if datetime_fields:
        for field in datetime_fields:
            value = out.get(field)
            if isinstance(value, datetime):
                out[field] = _to_iso_utc(value)
    else:
        for key, value in out.items():
            if isinstance(value, datetime):
                out[key] = _to_iso_utc(value)

    return out


def serialize_mongo_list(
    items: Iterable[dict[str, Any]],
    *,
    datetime_fields: set[str] | None = None,
    drop_fields: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Serialize a list of MongoDB documents using the same rules."""
    return [
        serialize_mongo_doc(
            item,
            datetime_fields=datetime_fields,
            drop_fields=drop_fields,
        )
        for item in items
    ]
