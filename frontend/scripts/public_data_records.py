"""Check the published manufacturing files and emit observed timeline intervals."""

import csv
from collections import defaultdict
from datetime import datetime, timedelta
from hashlib import md5
import json
from pathlib import Path
import sys
from xml.etree import ElementTree
from zipfile import ZipFile


def verified(path, checksum):
    with path.open("rb") as source:
        if md5(source.read(), usedforsecurity=False).hexdigest() != checksum:
            raise ValueError(f"Publisher checksum differs for {path.name}")
    return path


def csv_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def interval(identifier, start, end):
    return {"id": identifier, "start_hour": start, "end_hour": end}


def bottling_rows(path):
    with ZipFile(path) as workbook:
        shared = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
        strings = ["".join(item.itertext()) for item in shared]
        sheet = ElementTree.fromstring(workbook.read("xl/worksheets/sheet4.xml"))
    rows = [
        [cell.text for cell in row.findall("{*}c/{*}v")]
        for row in sheet.findall("{*}sheetData/{*}row")
    ]
    assert [strings[int(key)] for key in rows[0]] == [
        "downtime_id", "date", "downtime_start_time", "downtime_end_time", "downtime_time",
    ]
    days = defaultdict(list)
    for key, date, start, end, duration in rows[1:]:
        start, end, duration = map(float, (start, end, duration))
        assert 0 <= start < end < 1 and abs(end - start - duration) < 1e-10
        day = (datetime(1899, 12, 30) + timedelta(days=int(date))).date().isoformat()
        days[day].append(interval(strings[int(key)], start * 24, end * 24))
    assert sum(map(len, days.values())) == 1388 and len(days) == 55
    return {f"Bottling {day}": items for day, items in days.items()}


def cnc_rows(path):
    samples = [(datetime.fromisoformat(row["DateTime"]), row["Phase"]) for row in csv_rows(path)]
    assert len(samples) == 12388
    origin = samples[0][0]
    spans = []
    excluded_pairs = 0
    last_span_phase = None
    for (start, phase), (end, next_phase) in zip(samples, samples[1:]):
        gap = (end - start).total_seconds()
        if phase != next_phase or not 0 < gap <= 5:
            excluded_pairs += 1
            continue
        first = (start - origin).total_seconds() / 3600
        last = (end - origin).total_seconds() / 3600
        if spans and spans[-1]["end_hour"] == first and phase == last_span_phase:
            spans[-1]["end_hour"] = last
        else:
            spans.append(interval(f"{start.isoformat()} phase {phase}", first, last))
        last_span_phase = phase
    print(f"CNC: {len(samples)} observations, {len(spans)} spans, {excluded_pairs} pairs excluded")
    return {f"CNC {origin.date()}": spans}


def check_textile(directory):
    jobs = csv_rows(directory / "jobs.csv")
    families = csv_rows(directory / "families.csv")
    machines = csv_rows(directory / "machine_capacity.csv")
    setup = csv_rows(directory / "setup.csv")
    family_ids = {row["family_id"] for row in families}
    assert len(jobs) == len({row["job_id"] for row in jobs}) == 100
    assert len(families) == len(family_ids) == 5
    assert len(machines) == len({row["machine_id"] for row in machines}) == 10
    assert all(row["family"] in family_ids for row in jobs)
    assert len(setup) == 25
    assert {(row["j1"], row["j2"]) for row in setup} == {
        (left, right) for left in family_ids for right in family_ids
    }
    print("Textile: verified 100 orders, 5 families, 10 machines and 25 setup pairs")


def main(directory):
    workbook = verified(directory / "production_raw.xlsx", "d9c095d5eba8706ac7dda92af63f5c35")
    cnc = verified(directory / "Data_from_2021-11-26.csv", "a224915e93e797404117230811f2c077")
    verified(directory / "textile-dataset.rar", "64008b541a8207b2ad04d985bfc6d7aa")
    check_textile(directory / "Dataset/Data_i100_f5_k10")
    rows = bottling_rows(workbook) | cnc_rows(cnc)
    output = directory / "observed-timeline.json"
    output.write_text(json.dumps(rows), encoding="utf-8")
    print(f"Observed records: {output}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
