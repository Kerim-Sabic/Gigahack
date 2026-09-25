import os
import re

from fastapi import APIRouter, Depends, Request
from pydantic import Field

from .db import audit, canonical, transaction, uid
from .domain import Strict

router = APIRouter(prefix="/api/v1")


def admin(request: Request):
    from .main import fail, user

    u = user(request)
    if u["role"] != "admin":
        fail("admin_required", 403)
    return u


class Group(Strict):
    id: str | None = None
    version: int = 0
    name: str = Field(min_length=1, max_length=100)
    addresses: list[str] = Field(min_length=1, max_length=100)


@router.post("/recipient-groups")
def group(body: Group, u=Depends(admin)):
    from .main import fail

    domains = os.environ.get("MOM_ALLOWED_RECIPIENT_DOMAINS", "secure-mom.test").split(",")
    addresses = sorted(set(body.addresses))
    for address in addresses:
        if (
            not re.fullmatch(r"[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+", address)
            or address.rsplit("@", 1)[1] not in domains
        ):
            fail("recipient_outside_allowed_domains")
    with transaction() as c:
        if body.id:
            row = c.execute("SELECT * FROM recipient_groups WHERE id=?", (body.id,)).fetchone()
            if not row or row["version"] != body.version:
                fail("recipient_group_changed", 409)
            c.execute(
                "UPDATE recipient_groups SET name=?,version=version+1,addresses=? WHERE id=?",
                (body.name, canonical(addresses), body.id),
            )
            ident = body.id
        else:
            ident = uid()
            c.execute(
                "INSERT INTO recipient_groups VALUES(?,?,1,?)", (ident, body.name, canonical(addresses))
            )
        audit(c, None, u["id"], "recipient_group_updated", {"id": ident, "version": body.version + 1})
        return {"id": ident, "version": body.version + 1, "name": body.name, "addresses": addresses}


class Glossary(Strict):
    version: int
    terms: list[str] = Field(max_length=100)


@router.get("/settings/glossary")
def get_glossary(u=Depends(admin)):
    import json

    with transaction() as c:
        row = c.execute("SELECT * FROM settings WHERE key='glossary'").fetchone()
        return (
            {"version": row["version"], "terms": json.loads(row["body"])}
            if row
            else {"version": 0, "terms": []}
        )


@router.put("/settings/glossary")
def glossary(body: Glossary, u=Depends(admin)):
    from .main import fail

    if any(len(term) > 100 or "\n" in term for term in body.terms):
        fail("invalid_glossary_term")
    with transaction() as c:
        old = c.execute("SELECT version FROM settings WHERE key='glossary'").fetchone()
        if (old[0] if old else 0) != body.version:
            fail("revision_conflict", 409)
        c.execute(
            "INSERT INTO settings VALUES('glossary',?,?) ON CONFLICT(key) DO UPDATE SET version=excluded.version,body=excluded.body",
            (body.version + 1, canonical(body.terms)),
        )
        audit(c, None, u["id"], "glossary_updated", {"version": body.version + 1})
        return {"version": body.version + 1, "terms": body.terms}
