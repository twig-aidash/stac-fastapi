"""Ingest sample data during docker-compose"""
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests

workingdir = Path(__file__).parent.absolute()
joplindata = workingdir.parent / "stac_fastapi" / "testdata" / "joplin"

fo_data = workingdir.parent / "stac_fastapi" / "testdata" / "forest-observatory"

app_host = sys.argv[1]

if not app_host:
    raise Exception("You must include full path/port to stac instance")


def ingest_joplin_data(app_host: str = app_host, data_dir: Path = joplindata):
    """ingest data."""

    with open(data_dir / "collection.json") as f:
        collection = json.load(f)
    r = requests.post(urljoin(app_host, "collections"), json=collection)
    if r.status_code not in (200, 409):
        r.raise_for_status()

    with open(data_dir / "index.geojson") as f:
        index = json.load(f)

    for feat in index["features"]:
        del feat["stac_extensions"]
        r = requests.post(
            urljoin(app_host, f"collections/{collection['id']}/items"), json=feat
        )
        if r.status_code == 409:
            continue
        r.raise_for_status()

def ingest_forest_observatory_data(app_host: str = app_host, data_dir: Path=fo_data):
    "ingest forest observatory data"
    with open(data_dir / "collection.json") as f:
        collection = json.load(f)
    
    links = collection["links"]
    collection["links"] = []
    r = requests.post(urljoin(app_host, "collections"), json=collection)
    if r.status_code not in (200, 409):
        r.raise_for_status()
    features = []

    for link in links:
        if (link["type"] != "application/json") or (link["rel"] != "item"):
            continue
        r_feature = requests.get(link["href"])
        if r_feature.status_code not in (200, 409):
            r_feature.raise_for_status()
        features.append(r_feature.json())

    for feat in features:
        r = requests.post(
            urljoin(app_host, f"collections/{collection['id']}/items"), json=feat
        )
        if r.status_code == 409:
            continue
        r.raise_for_status()

if __name__ == "__main__":
    ingest_joplin_data()
    ingest_forest_observatory_data()
