#!/usr/bin/env python3.9
import sys
import json
import importlib.util

spec = importlib.util.spec_from_file_location(
    "Recommendations-handler",
    "/workshop/AWS-CloudHacks-2026/backend/lambda/Recommendations-handler.py"
)
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

result = pipeline.get_recommendations("demo", 4500)
print(json.dumps(result, indent=2, default=str))
