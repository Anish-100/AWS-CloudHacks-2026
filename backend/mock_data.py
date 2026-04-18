from decimal import Decimal

MOCK_TRANSACTIONS = [
    {"tx_date": "2025-03-01", "amount": Decimal("12.50"),  "category": "dining",        "specs": "coffee shop",  "anomaly_flag": False},
    {"tx_date": "2025-03-02", "amount": Decimal("84.20"),  "category": "groceries",     "specs": "supermarket",  "anomaly_flag": False},
    {"tx_date": "2025-03-03", "amount": Decimal("9.99"),   "category": "subscriptions", "specs": "streaming",    "anomaly_flag": False},
    {"tx_date": "2025-03-04", "amount": Decimal("47.30"),  "category": "dining",        "specs": "restaurant",   "anomaly_flag": False},
    {"tx_date": "2025-03-05", "amount": Decimal("220.00"), "category": "shopping",      "specs": "clothing",     "anomaly_flag": True},
    {"tx_date": "2025-03-07", "amount": Decimal("15.00"),  "category": "transport",     "specs": "rideshare",    "anomaly_flag": False},
    {"tx_date": "2025-03-08", "amount": Decimal("63.40"),  "category": "dining",        "specs": "restaurant",   "anomaly_flag": False},
    {"tx_date": "2025-03-10", "amount": Decimal("34.99"),  "category": "subscriptions", "specs": "software",     "anomaly_flag": False},
    {"tx_date": "2025-03-11", "amount": Decimal("11.20"),  "category": "dining",        "specs": "coffee shop",  "anomaly_flag": False},
    {"tx_date": "2025-03-12", "amount": Decimal("92.00"),  "category": "groceries",     "specs": "supermarket",  "anomaly_flag": False},
    {"tx_date": "2025-03-14", "amount": Decimal("180.00"), "category": "shopping",      "specs": "electronics",  "anomaly_flag": True},
    {"tx_date": "2025-03-15", "amount": Decimal("8.50"),   "category": "transport",     "specs": "rideshare",    "anomaly_flag": False},
    {"tx_date": "2025-03-16", "amount": Decimal("55.75"),  "category": "dining",        "specs": "restaurant",   "anomaly_flag": False},
    {"tx_date": "2025-03-18", "amount": Decimal("14.99"),  "category": "subscriptions", "specs": "streaming",    "anomaly_flag": False},
    {"tx_date": "2025-03-19", "amount": Decimal("29.00"),  "category": "transport",     "specs": "gas",          "anomaly_flag": False},
    {"tx_date": "2025-03-20", "amount": Decimal("76.50"),  "category": "groceries",     "specs": "supermarket",  "anomaly_flag": False},
    {"tx_date": "2025-03-21", "amount": Decimal("38.90"),  "category": "dining",        "specs": "restaurant",   "anomaly_flag": False},
    {"tx_date": "2025-03-23", "amount": Decimal("9.99"),   "category": "subscriptions", "specs": "music",        "anomaly_flag": False},
    {"tx_date": "2025-03-25", "amount": Decimal("310.00"), "category": "shopping",      "specs": "furniture",    "anomaly_flag": True},
    {"tx_date": "2025-03-27", "amount": Decimal("22.00"),  "category": "transport",     "specs": "rideshare",    "anomaly_flag": False},
    {"tx_date": "2025-03-28", "amount": Decimal("67.80"),  "category": "groceries",     "specs": "supermarket",  "anomaly_flag": False},
    {"tx_date": "2025-03-30", "amount": Decimal("41.25"),  "category": "dining",        "specs": "restaurant",   "anomaly_flag": False},
]

MOCK_GOAL = {
    "goal_id":         "goal_001",
    "type":            "short",
    "description":     "Save for a new laptop",
    "target_amount":   Decimal("800.00"),
    "current_savings": Decimal("120.00"),
    "deadline":        "2025-06-01",
}

USER_INCOME_MONTHLY = 4500