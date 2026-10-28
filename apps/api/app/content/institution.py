"""Mock organizations and accounts for the institution workspace (S2-01, ADR-15).

Demo data only: no passwords, tokens or sessions. The web sends a picked account as `X-Demo-Account`.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator

from app.domain.case import Model, NonBlank

DemoRole = Literal["org_admin", "educator", "reviewer", "learner"]
STAFF_ROLES: frozenset[str] = frozenset({"org_admin", "educator"})


class DemoOrg(Model):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name_th: NonBlank


class DemoAccount(Model):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    org_id: str | None = None
    display_name_th: NonBlank
    role: DemoRole
    partner_id: str | None = None


class Institutions(Model):
    demo: Literal[True]
    orgs: list[DemoOrg] = Field(min_length=1)
    accounts: list[DemoAccount] = Field(min_length=1)

    @model_validator(mode="after")
    def references(self) -> "Institutions":
        org_ids = {o.id for o in self.orgs}
        ids = [a.id for a in self.accounts]
        if len(org_ids) != len(self.orgs) or len(set(ids)) != len(ids):
            raise ValueError("duplicate org or account ID")
        by_id = {a.id: a for a in self.accounts}
        for account in self.accounts:
            if account.org_id is not None and account.org_id not in org_ids:
                raise ValueError(f"{account.id}: unknown org")
            if account.role != "learner" and account.org_id is None:
                raise ValueError(f"{account.id}: staff need an org")
            if account.partner_id is not None:
                other = by_id.get(account.partner_id)
                if other is None or other.partner_id != account.id or account.role != "learner":
                    raise ValueError(f"{account.id}: partner must be a learner who points back")
        for org in self.orgs:
            roles = [a.role for a in self.accounts if a.org_id == org.id]
            if "org_admin" not in roles or "educator" not in roles:
                raise ValueError(f"{org.id}: needs an org_admin and an educator")
        return self


def load_institutions(content_dir: Path) -> Institutions:
    path = content_dir / "demo" / "institutions.yaml"
    return Institutions.model_validate(yaml.safe_load(path.read_text("utf-8")))


@lru_cache
def institutions(content_dir: Path) -> Institutions:
    """Cached per content dir: the file is static for the life of the process."""
    return load_institutions(content_dir)
