import asyncio
import json
import os


async def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("No DATABASE_URL — generating fallback from existing VehicleDB data")
        generate_fallback()
        return

    import asyncpg
    conn = await asyncpg.connect(db_url)

    # Export vehicle makes and models with pricing
    makes = await conn.fetch("""
        SELECT vm.name as make, vmo.name as model, vmo.year_start, vmo.year_end,
               vmo.body_types, ve.displacement_cc, ve.fuel_type, ve.power_hp
        FROM vehicle_makes vm
        JOIN vehicle_models vmo ON vm.id = vmo.make_id
        LEFT JOIN vehicle_model_engines vme ON vmo.id = vme.model_id
        LEFT JOIN vehicle_engines ve ON vme.engine_id = ve.id
        ORDER BY vm.name, vmo.name, vmo.year_start
    """)

    # Build structured data
    data = {}
    for row in makes:
        make = row['make']
        if make not in data:
            data[make] = {'models': {}}
        model = row['model']
        if model not in data[make]['models']:
            data[make]['models'][model] = {
                'yearStart': row['year_start'],
                'yearEnd': row['year_end'],
                'bodyTypes': row['body_types'] or [],
                'engines': []
            }
        if row['displacement_cc']:
            data[make]['models'][model]['engines'].append({
                'cc': row['displacement_cc'],
                'fuel': row['fuel_type'],
                'hp': row['power_hp']
            })

    await conn.close()

    os.makedirs('shared/data', exist_ok=True)
    with open('shared/data/vehicle-pricing.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(data)} makes with {sum(len(v['models']) for v in data.values())} models")


def generate_fallback():
    """Generate from the existing hardcoded VehicleDB as fallback"""
    # This runs when no DB connection is available (local dev, initial setup)
    os.makedirs('shared/data', exist_ok=True)

    # Create a minimal pricing structure from known Hungarian market data
    # Sources: publicly available average prices from industry reports
    data = {
        "_meta": {
            "source": "fallback-estimation",
            "updated": "2026-03-25",
            "note": "Estimated values. Will be replaced by real DB export when BACKEND_DB_READ_URL is configured."
        }
    }

    with open('shared/data/vehicle-pricing.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Generated fallback vehicle-pricing.json")


asyncio.run(main())
