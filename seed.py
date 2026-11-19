"""Deterministic, idempotent synthetic MIM factory dataset."""

from __future__ import annotations

import asyncio
import os
import random

from sqlalchemy import delete

from database import SessionLocal, init_db
from domain import ALLOYS, SEGMENTS, STAGES
from models import Part, Resource, ScheduleVersion, ScheduledOperation, WorkOrder

SEED = 20261118
RECIPES = {
    "MIM-17-4PH": "R-17-4PH-H900",
    "MIM-316L": "R-316L-VAC",
    "MIM-4605": "R-4605-CARB",
    "Ti-6Al-4V": "R-TI64-HIP",
}


def make_resources() -> list[Resource]:
    all_alloys = list(ALLOYS)
    resources: list[Resource] = []
    definitions = [
        ("Hoskote", "Molding", [("M-1", all_alloys), ("M-2", all_alloys)]),
        ("Doddaballapura", "Molding", [("M-3", all_alloys), ("M-4", all_alloys)]),
        ("Hoskote", "Debinding", [("D-1", all_alloys), ("D-2", all_alloys)]),
        ("Doddaballapura", "Debinding", [("D-3", all_alloys)]),
        ("Hoskote", "Sintering", [("F-1", ["MIM-17-4PH", "MIM-316L"]), ("F-2", ["MIM-17-4PH", "MIM-316L"])]),
        ("Doddaballapura", "Sintering", [("F-3", ["MIM-4605", "Ti-6Al-4V"]), ("F-4", ["MIM-4605", "Ti-6Al-4V"])]),
        ("Hoskote", "CNC Machining", [("CNC-1", all_alloys), ("CNC-2", all_alloys)]),
        ("Doddaballapura", "CNC Machining", [("CNC-3", all_alloys), ("CNC-4", all_alloys)]),
        ("Hoskote", "Finishing", [("FIN-1", all_alloys), ("FIN-2", all_alloys)]),
        ("Doddaballapura", "Finishing", [("FIN-3", all_alloys)]),
    ]
    for plant, stage, entries in definitions:
        for name, alloys in entries:
            if stage == "Sintering":
                recipes = [RECIPES[item] for item in alloys]
                capacity = 360 if plant == "Hoskote" else 300
                setup = 0
            elif stage == "CNC Machining":
                recipes = []
                capacity = 1
                setup = {"CNC-1": 100, "CNC-2": 125, "CNC-3": 145, "CNC-4": 110}[name]
            elif stage == "Debinding":
                recipes = []
                capacity = {"D-1": 240, "D-2": 220, "D-3": 200}[name]
                setup = 15
            else:
                recipes = []
                capacity = 1
                setup = 10 if stage == "Molding" else 25
            resources.append(Resource(
                id=name,
                name=name,
                plant=plant,
                stage=stage,
                capacity_units=capacity,
                alloy_compatibility=alloys,
                recipe_compatibility=recipes,
                setup_changeover_mins=setup,
                status="ACTIVE",
            ))
    assert len(resources) == 18
    return resources


def make_parts(rng: random.Random) -> list[Part]:
    parts: list[Part] = []
    per_unit_cycles = {
        "Molding": (1.0, 2.8),
        "CNC Machining": (2.0, 5.0),
        "Finishing": (0.7, 2.2),
    }
    batch_cycles = {
        "Debinding": (300, 510),
        "Sintering": (390, 720),
    }
    for i in range(50):
        alloy = ALLOYS[i % len(ALLOYS)]
        segment = SEGMENTS[(i * 3 + i // 4) % len(SEGMENTS)]
        machining = not (segment == "ECM" and i % 4 == 0)
        cycles = {
            stage: round(rng.uniform(*per_unit_cycles[stage]), 2)
            for stage in ("Molding", "CNC Machining", "Finishing")
        }
        cycles.update({stage: rng.randint(*batch_cycles[stage]) for stage in batch_cycles})
        parts.append(Part(
            id=f"part-{i + 1:03d}",
            sku_code=f"IF-{segment[:3].upper()}-{i + 1:03d}",
            name=f"{segment} precision component {i + 1:02d}",
            segment=segment,
            alloy_family=alloy,
            sintering_recipe_id=RECIPES[alloy],
            cycle_times_mins=cycles,
            requires_machining=machining,
        ))
    return parts


def make_work_orders(parts: list[Part], rng: random.Random, resources: list[Resource] | None = None) -> list[WorkOrder]:
    stage_weights = [0.34, 0.20, 0.19, 0.18, 0.09]
    orders: list[WorkOrder] = []
    for i in range(150):
        part = parts[rng.randrange(len(parts))]
        current_stage = rng.choices(STAGES, weights=stage_weights, k=1)[0]
        priority = rng.choices([1, 2, 3, 4, 5], weights=[0.08, 0.14, 0.38, 0.27, 0.13], k=1)[0]
        due = rng.randint(40, 210)
        if part.segment in ("Aerospace", "Medical") and priority >= 4:
            due = rng.randint(28, 105)
        age = round(rng.uniform(0, 62), 1)
        status = "LATE_RISK" if due < 72 or (age > 42 and priority >= 4) else "QUEUED"
        plant = None
        if resources is not None:
            compatible_furnace = next(
                resource for resource in resources
                if resource.stage == "Sintering"
                and part.alloy_family in (resource.alloy_compatibility or [])
                and (not resource.recipe_compatibility or part.sintering_recipe_id in resource.recipe_compatibility)
            )
            plant = compatible_furnace.plant
        orders.append(WorkOrder(
            id=f"wo-{i + 1:04d}",
            wo_number=f"WO-26-{i + 1:04d}",
            part_id=part.id,
            plant=plant,
            quantity=rng.randint(18, 75),
            due_date_hours=float(due),
            priority=priority,
            current_stage=current_stage,
            status=status,
            wip_age_hours=age,
        ))
    return orders


async def seed_database() -> dict[str, int]:
    production = os.getenv("APP_ENV", "development").lower() == "production"
    if production and os.getenv("ENABLE_PRODUCTION_SEED", "false").lower() != "true":
        raise RuntimeError("Production seeding is disabled; set ENABLE_PRODUCTION_SEED=true explicitly")
    if not production:
        await init_db()
    async with SessionLocal() as session:
        for model in (ScheduledOperation, ScheduleVersion, WorkOrder, Part, Resource):
            await session.execute(delete(model))
        rng = random.Random(SEED)
        resources = make_resources()
        parts = make_parts(rng)
        orders = make_work_orders(parts, rng, resources)
        session.add_all(resources + parts + orders)
        await session.commit()
    return {"resources": len(resources), "parts": len(parts), "work_orders": len(orders)}


if __name__ == "__main__":
    print(asyncio.run(seed_database()))
