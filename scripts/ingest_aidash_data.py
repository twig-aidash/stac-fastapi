"""Ingest sample data during docker-compose"""
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests

app_host_source = sys.argv[1]
app_host_sink = sys.argv[2]

def ingest_aidash_data(app_host_source: str = app_host_source, app_host_sink: Path=app_host_sink):
    """fetch items in collections present in the following list"""
    
    collection_ids = ["sentinel-s1-l2", "dsm", "optical_imagery"]
    collections = []
    headers = {"token": "API_TOKEN"}

    for collection_id in collection_ids:
        collection = requests.get(f"{app_host_source}/collections/{collection_id}", headers=headers).json()
        collections.append(collection)


    """push collections"""
    
    for collection in collections:
        result = requests.post(f"{app_host_sink}/collections", json=collection)
        if result.status_code == 409:
            continue
    
    """fetch items in collections and push items"""

    items = []
    for collection_id in collection_ids:
        # look for features until available
        next_items_url = f"{app_host_source}/collections/{collection_id}/items?limit=1000"
        while next_items_url:
            print(next_items_url)
            next_items_url = next_items_url.replace("prodcollections", "prod/collections")
            items_current = requests.get(next_items_url, headers=headers).json()
            items += items_current["features"]

            # check if next link exists

            links = items_current["links"]
            next_items_url_query = [elem for elem in links if elem["rel"] == "next"]
            if len(next_items_url_query) != 0:
                next_items_url = next_items_url_query[0]["href"]
            else:
                next_items_url = None
    
    # iterate through features and push items
    for item in items:
        collection_id = item["collection"]
        r = requests.post(
            f"{app_host_sink}/collections/{collection_id}/items", json=item
        )
        if r.status_code == 409:
            continue
        r.raise_for_status()
        


if __name__ == "__main__":
    ingest_aidash_data()
