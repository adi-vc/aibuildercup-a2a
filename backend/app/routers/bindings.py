"""
bindings.py — POST /v1/bindings/resolve (vachan-plan.md §35, §24.2 rung 1).

The play-time resolver for volatile values. The runtime calls it with the
viewer's city and falls down the §24.2 ladder (cache → published fact →
neutral) on any failure, so this endpoint is never the guarantee — it is
only the freshest rung.

The feed is a config-held stand-in for a dealer pricing system. Its default
values equal the published fixture prices, so a city swap rebinds to the
same number the source page cites (§19 moment 6). Set BINDINGS_FAIL=1 to
kill the resolver and exercise the fallback rungs (§64.7 criterion 5).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/v1/bindings", tags=["bindings"])

RESOLVER_FOR_KEY = {"price": "offer.by_city"}


class ResolveRequest(BaseModel):
    keys: list[str]
    city: str
    sku: str = "vega_v1"


def resolve_live(key: str, city: str) -> dict | None:
    """One binding value for the guard's volatile answers (§30 #8); None when the resolver is down."""
    if settings.bindings_fail:
        return None
    value = _resolve(key, city)
    return {**value, "resolved_at": datetime.now(timezone.utc).isoformat()} if value else None


def _resolve(key: str, city: str) -> dict | None:
    if RESOLVER_FOR_KEY.get(key) == "offer.by_city":
        amount = settings.live_offer_feed.get(city.lower())
        if amount is not None:
            return {"value": str(amount), "unit": "INR", "resolver": "offer.by_city"}
    return None


@router.post("/resolve")
async def resolve_bindings(body: ResolveRequest) -> JSONResponse:
    """Resolve each key for the viewer's city; unresolvable keys are omitted, never guessed."""
    if settings.bindings_fail:
        raise HTTPException(status_code=503, detail="Binding resolver unavailable (BINDINGS_FAIL).")
    values = {key: v for key in body.keys if (v := _resolve(key, body.city)) is not None}
    return JSONResponse(
        content={
            "values": values,
            "city": body.city.lower(),
            "sku": body.sku,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        },
        # Freshness is owned by the client's TTL/SWR cache (§49 C5), not HTTP caches.
        headers={"Cache-Control": "no-store"},
    )
