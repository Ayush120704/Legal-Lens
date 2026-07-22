"""
Deployment configuration checker.
Run this to verify your production environment is properly configured.
Usage:  python deploy_check.py
"""

import os
import sys


def check():
    errors = []
    warnings = []

    # Detect environment
    is_render = "RENDER" in os.environ
    is_railway = "RAILWAY_SERVICE_ID" in os.environ
    is_fly = "FLY_APP_NAME" in os.environ
    is_production = is_render or is_railway or is_fly or os.getenv("PRODUCTION", "").lower() in ("1", "true", "yes")

    print("=" * 60)
    print("LegalLens Deployment Configuration Check")
    print("=" * 60)

    # SECRET_KEY
    sk = os.getenv("SECRET_KEY", "")
    if not sk:
        errors.append("SECRET_KEY is not set. Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"")
    elif sk == "change-this-to-a-random-secret-key-in-production":
        errors.append("SECRET_KEY is still the placeholder value. Generate a real one.")
    elif len(sk) < 32:
        errors.append("SECRET_KEY is too short (< 32 chars). Generate a stronger one.")
    else:
        print(f"  [OK] SECRET_KEY is set ({len(sk)} chars)")

    # ALLOWED_ORIGINS
    origins = os.getenv("ALLOWED_ORIGINS", "")
    if is_production:
        if not origins:
            errors.append("ALLOWED_ORIGINS is not set. Set it to your frontend URL.")
        elif "localhost" in origins and not is_render and not is_railway and not is_fly:
            warnings.append("ALLOWED_ORIGINS contains localhost — make sure this is intentional for production.")
        else:
            print(f"  [OK] ALLOWED_ORIGINS is set: {origins}")
    else:
        print(f"  [OK] ALLOWED_ORIGINS: {origins or 'not set (dev mode)'}")

    # DATABASE_URL
    db_url = os.getenv("DATABASE_URL", "sqlite:///./legal_analyzer.db")
    if is_production and "sqlite" in db_url:
        errors.append("DATABASE_URL is using SQLite. Switch to PostgreSQL for production: DATABASE_URL=postgresql://user:pass@host:5432/legallens")
    elif "postgresql" in db_url:
        print(f"  [OK] DATABASE_URL: PostgreSQL")
    else:
        print(f"  [OK] DATABASE_URL: {db_url}")

    # OPENAI_API_KEY (optional)
    oai = os.getenv("OPENAI_API_KEY", "")
    if oai:
        print(f"  [OK] OPENAI_API_KEY is set ({len(oai)} chars)")
    else:
        print(f"  [OK] OPENAI_API_KEY not set (local fallback will be used)")

    # RATE_LIMIT
    rl = os.getenv("RATE_LIMIT_PER_MINUTE", "60")
    print(f"  [OK] Rate limit: {rl} req/min")

    # Summary
    print()
    print("=" * 60)
    if errors:
        print(f"  FAILED: {len(errors)} error(s) to fix:")
        for e in errors:
            print(f"    - {e}")
    if warnings:
        print(f"  WARNINGS: {len(warnings)}:")
        for w in warnings:
            print(f"    - {w}")
    if not errors:
        print("  PASSED: Configuration looks good!")
    print("=" * 60)

    return len(errors) == 0


if __name__ == "__main__":
    success = check()
    sys.exit(0 if success else 1)
