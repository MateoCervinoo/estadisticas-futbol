from __future__ import annotations
from typing import Dict, Optional, Set
from sqlmodel import Session, select
from ..models import Equipo


class TeamMapper:
    def __init__(self, session: Session):
        self.session = session
        self._cache: Dict[str, Optional[int]] = {}
        self._load_all()

    def _load_all(self):
        equipos = self.session.exec(select(Equipo)).all()
        for eq in equipos:
            for attr in ("nombre_canonico", "nombre_api", "nombre_csv", "nombre_fbref", "nombre_understat", "nombre_es"):
                val = getattr(eq, attr, None)
                if val:
                    key = self._normalize(val)
                    if key not in self._cache:
                        self._cache[key] = eq.id

    def _normalize(self, name: str) -> str:
        return name.lower().strip().replace("-", " ").replace("_", " ")

    def resolve(self, name: str) -> Optional[int]:
        key = self._normalize(name)
        return self._cache.get(key)

    def resolve_or_create(self, name: str, tipo: str = "seleccion") -> int:
        existing = self.resolve(name)
        if existing is not None:
            return existing
        eq = Equipo(nombre_canonico=name, nombre_csv=name, tipo=tipo)
        self.session.add(eq)
        self.session.flush()
        norm = self._normalize(name)
        self._cache[norm] = eq.id
        return eq.id

    def register_alias(self, canonical_name: str, alias_name: str, attr: str = "nombre_api"):
        key = self._normalize(alias_name)
        eq = self.session.exec(select(Equipo).where(Equipo.nombre_canonico == canonical_name)).first()
        if eq:
            setattr(eq, attr, alias_name)
            self._cache[key] = eq.id
