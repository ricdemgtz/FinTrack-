import re

def apply_rules(rules, tx_dict):
    """Apply simple rules to a transaction dict.
    rules: iterable of dicts: {pattern, field, min_amount, max_amount, category_id, active, priority}
    tx_dict: {merchant, note, amount}
    """
    candidates = sorted([r for r in rules if r.get("active", True)], key=lambda r: r.get("priority", 100))
    for r in candidates:
        field_val = (tx_dict.get("note") if r.get("field") == "note" else tx_dict.get("merchant")) or ""
        ok = False
        pat = r.get("pattern","")
        if pat.startswith("re:"):
            ok = re.search(pat[3:], field_val, re.I) is not None
        else:
            ok = pat.lower() in field_val.lower()

        amt = float(tx_dict.get("amount", 0))
        if r.get("min_amount") is not None and amt < float(r["min_amount"]): ok = False
        if r.get("max_amount") is not None and amt > float(r["max_amount"]): ok = False

        if ok:
            return r.get("category_id")
    return None
