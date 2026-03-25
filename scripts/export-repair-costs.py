import asyncio
import json
import os


async def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("No DATABASE_URL — skipping repair cost export")
        generate_fallback()
        return

    import asyncpg
    conn = await asyncpg.connect(db_url)

    # Export DTC-to-cost mapping
    costs = await conn.fetch("""
        SELECT dc.code, ki.title, ki.estimated_cost_min, ki.estimated_cost_max,
               ki.labor_hours, ki.severity
        FROM dtc_codes dc
        JOIN known_issues ki ON dc.id = ki.dtc_code_id
        WHERE ki.estimated_cost_min IS NOT NULL
        ORDER BY dc.code
    """)

    data = {}
    for row in costs:
        code = row['code']
        if code not in data:
            data[code] = []
        data[code].append({
            'issue': row['title'],
            'costMin': row['estimated_cost_min'],
            'costMax': row['estimated_cost_max'],
            'laborHours': float(row['labor_hours']) if row['labor_hours'] else None,
            'severity': row['severity']
        })

    await conn.close()

    os.makedirs('shared/data', exist_ok=True)
    with open('shared/data/repair-costs.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"Exported repair costs for {len(data)} DTC codes")


def generate_fallback():
    os.makedirs('shared/data', exist_ok=True)
    data = {"_meta": {"source": "fallback", "updated": "2026-03-25"}}
    with open('shared/data/repair-costs.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    print("Generated fallback repair-costs.json")


asyncio.run(main())
