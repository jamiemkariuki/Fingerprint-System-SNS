#!/usr/bin/env python3

import os

# Check environment variables
print("Environment Variables:")
print(f"USE_POSTGRES: {os.getenv('USE_POSTGRES')}")
print(f"USE_SQLITE: {os.getenv('USE_SQLITE')}")
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")

# Check how they're being interpreted
use_postgres = os.getenv("USE_POSTGRES", "").lower() in ("1", "true", "yes")
use_sqlite = os.getenv("USE_SQLITE", "").lower() in ("1", "true", "yes")

print(f"\nInterpreted Values:")
print(f"use_postgres: {use_postgres}")
print(f"use_sqlite: {use_sqlite}")
print(f"not USE_SQLITE: {not use_sqlite}")
print(f"not USE_POSTGRES: {not use_postgres}")
print(f"not USE_SQLITE and not USE_POSTGRES: {not use_sqlite and not use_postgres}")
