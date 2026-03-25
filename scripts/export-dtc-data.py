import asyncio
import json
import os


async def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("No DATABASE_URL — generating fallback DTC data")
        generate_fallback()
        return

    import asyncpg
    conn = await asyncpg.connect(db_url)

    dtc_codes = await conn.fetch("""
        SELECT code, description_en, description_hu, category, is_generic, severity
        FROM dtc_codes
        ORDER BY code
    """)

    data = {}
    for row in dtc_codes:
        data[row['code']] = {
            'en': row['description_en'],
            'hu': row['description_hu'],
            'category': row['category'],
            'generic': row['is_generic'],
            'severity': row['severity']
        }

    await conn.close()

    os.makedirs('shared/data', exist_ok=True)
    with open('shared/data/dtc-database.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"Exported {len(data)} DTC codes")


def generate_fallback():
    os.makedirs('shared/data', exist_ok=True)
    data = {"_meta": {"source": "fallback", "updated": "2026-03-25"}}
    with open('shared/data/dtc-database.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    print("Generated fallback dtc-database.json")


asyncio.run(main())
