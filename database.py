"""
database.py  —  No-database replacement
========================================
All data is persisted to portfolio_store.json in the working directory.
"""

import json
import os
import uuid
from datetime import datetime

STORE_FILE = "portfolio_store.json"


def _load() -> dict:
    if os.path.exists(STORE_FILE):
        try:
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"portfolio": [], "alerts": [], "decisions": []}


def _save(data: dict):
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


class Portfolio:
    def __init__(self, symbol, quantity, buy_price,
                 current_price, invested_amount, market="US"):
        self.id              = str(uuid.uuid4())
        self.symbol          = symbol
        self.quantity        = quantity
        self.buy_price       = buy_price
        self.current_price   = current_price
        self.invested_amount = invested_amount
        self.market          = market
        self.is_active       = True
        self.bought_at       = datetime.now().isoformat()

    def to_dict(self):
        return self.__dict__.copy()

    @staticmethod
    def from_dict(d: dict):
        obj = Portfolio.__new__(Portfolio)
        obj.__dict__.update(d)
        return obj


class Alert:
    def __init__(self, symbol: str, message: str, alert_type: str):
        self.id         = str(uuid.uuid4())
        self.symbol     = symbol
        self.message    = message
        self.alert_type = alert_type
        self.created_at = datetime.now().isoformat()
        self.sent_at    = self.created_at

    def to_dict(self):
        return self.__dict__.copy()

    @staticmethod
    def from_dict(d: dict):
        obj = Alert.__new__(Alert)
        obj.__dict__.update(d)
        if not hasattr(obj, "sent_at"):
            obj.sent_at = d.get("created_at", "")
        if not hasattr(obj, "created_at"):
            obj.created_at = d.get("sent_at", "")
        return obj


class AIDecision:
    def __init__(self, symbol, action, confidence,
                 reason, price_at_decision, technical_score):
        self.id                = str(uuid.uuid4())
        self.symbol            = symbol
        self.action            = action
        self.confidence        = confidence
        self.reason            = reason
        self.price_at_decision = price_at_decision
        self.technical_score   = technical_score
        self.created_at        = datetime.now().isoformat()

    def to_dict(self):
        return self.__dict__.copy()

    @staticmethod
    def from_dict(d: dict):
        obj = AIDecision.__new__(AIDecision)
        obj.__dict__.update(d)
        return obj


class _Session:
    def __init__(self):
        self._data  = _load()
        self._dirty = False

    def query(self, model_cls):
        return _Query(self._data, model_cls, self)

    def add(self, obj):
        key = _model_key(obj)
        self._data[key].append(obj.to_dict())
        self._dirty = True

    def commit(self):
        _save(self._data)
        self._dirty = False

    def close(self):
        if self._dirty:
            _save(self._data)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def SessionLocal() -> _Session:
    return _Session()


def _model_key(obj) -> str:
    if isinstance(obj, Portfolio):
        return "portfolio"
    if isinstance(obj, Alert):
        return "alerts"
    if isinstance(obj, AIDecision):
        return "decisions"
    raise ValueError(f"Unknown model type: {type(obj)}")


class _Query:
    def __init__(self, data: dict, model_cls, session: _Session):
        self._data       = data
        self._cls        = model_cls
        self._session    = session
        self._filters    = {}
        self._order_desc = False
        self._limit_n    = None

        if model_cls is Portfolio:
            self._key = "portfolio"
        elif model_cls is Alert:
            self._key = "alerts"
        elif model_cls is AIDecision:
            self._key = "decisions"
        else:
            self._key = "portfolio"

    def filter_by(self, **kwargs):
        self._filters.update(kwargs)
        return self

    def order_by(self, *_):
        self._order_desc = True
        return self

    def limit(self, n: int):
        self._limit_n = n
        return self

    def _results(self):
        rows = list(self._data.get(self._key, []))
        for k, v in self._filters.items():
            rows = [r for r in rows if r.get(k) == v]
        if self._order_desc and rows:
            date_field = "created_at" if "created_at" in rows[0] else "bought_at"
            rows = sorted(rows, key=lambda r: r.get(date_field, ""), reverse=True)
        if self._limit_n:
            rows = rows[: self._limit_n]
        return rows

    def all(self):
        rows = self._results()
        return [self._cls.from_dict(r) for r in rows]

    def first(self):
        results = self.all()
        return results[0] if results else None


def init_db():
    pass