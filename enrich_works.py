"""Enriquece los works en Neon con datos de fuentes gratuitas adicionales.

Orden de ejecución:
  1. DOAJ        — verifica revistas en DOAJ + APC real
  2. Unpaywall   — URLs OA + oa_status más fino
  3. ROR         — resuelve affiliaciones declared_unresolved
  4. OpenCitations — citas cruzadas para validación

Prerrequisito: correr migrate.py una vez antes del primer enrich.

Uso:
  python migrate.py          # solo la primera vez
  python enrich_works.py     # enriquece todos los works actuales
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv("backend/.env")

import psycopg2

DATABASE_URL   = os.getenv("DATABASE_URL", "")
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "auditoria@uacj.mx")

from backend.extractors import doaj, unpaywall, ror, opencitations


def main():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL no configurada en backend/.env")
        sys.exit(1)

    print("Conectando a Neon...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    # ── 1. DOAJ ──────────────────────────────────────────────────────────────
    print("\n[1/4] DOAJ — verificando revistas...")
    print("      (hace 1 llamada a OpenAlex + 1 a DOAJ por work, puede tardar ~2 min)")
    try:
        stats = doaj.enrich(conn, OPENALEX_EMAIL)
        print(f"      ✓ {stats['processed']} procesados | "
              f"{stats['doaj_found']} en DOAJ | "
              f"{stats['apc_updated']} APC reales guardados")
    except Exception as e:
        print(f"      ✗ Error: {e}")

    # ── 2. Unpaywall ─────────────────────────────────────────────────────────
    print("\n[2/4] Unpaywall — enriqueciendo datos OA...")
    try:
        stats = unpaywall.enrich(conn, OPENALEX_EMAIL)
        print(f"      ✓ {stats['processed']} procesados | "
              f"{stats['updated']} actualizados")
    except Exception as e:
        print(f"      ✗ Error: {e}")

    # ── 3. ROR ───────────────────────────────────────────────────────────────
    print("\n[3/4] ROR — resolviendo affiliaciones declaradas...")
    try:
        stats = ror.enrich(conn)
        print(f"      ✓ {stats['processed']} procesados | "
              f"{stats['resolved']} affiliaciones resueltas")
    except Exception as e:
        print(f"      ✗ Error: {e}")

    # ── 4. OpenCitations ─────────────────────────────────────────────────────
    print("\n[4/4] OpenCitations — contando citas cruzadas...")
    try:
        stats = opencitations.enrich(conn)
        print(f"      ✓ {stats['processed']} procesados | "
              f"{stats['updated']} actualizados")
    except Exception as e:
        print(f"      ✗ Error: {e}")

    conn.close()
    print("\nEnriquecimiento completado.")


if __name__ == "__main__":
    main()
