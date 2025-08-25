import pytest

from services.api.app.classify import apply_rules


def test_apply_rules_priority_and_active():
    rules = [
        {"pattern": "coffee", "category_id": 1, "priority": 50},
        {"pattern": "coffee", "category_id": 2, "priority": 10, "active": False},
    ]
    tx = {"merchant": "Coffee Shop", "note": "", "amount": 5}
    assert apply_rules(rules, tx) == 1


def test_apply_rules_regex_amount_and_field():
    rules = [
        {
            "pattern": "re:taxi$",
            "field": "note",
            "category_id": 3,
            "min_amount": 10,
            "max_amount": 30,
        }
    ]
    tx_ok = {"merchant": "Uber", "note": "night taxi", "amount": 20}
    assert apply_rules(rules, tx_ok) == 3
    tx_low = {"merchant": "Uber", "note": "night taxi", "amount": 5}
    assert apply_rules(rules, tx_low) is None
