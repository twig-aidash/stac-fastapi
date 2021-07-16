"""Item crud client."""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import attr
import orjson
from buildpg import render
from fastapi.responses import ORJSONResponse
from stac_pydantic import Collection, Item, ItemCollection
from stac_pydantic.api import ConformanceClasses, LandingPage
from stac_pydantic.shared import Link, MimeTypes, Relations

from stac_fastapi.pgstac.models.links import CollectionLinks, ItemLinks, PagingLinks
from stac_fastapi.pgstac.types.search import PgstacSearch
from stac_fastapi.types.core import BaseCoreClient
from stac_fastapi.types.errors import NotFoundError

NumType = Union[float, int]

from stac_fastapi.pgstac.config import Settings

settings = Settings()

@attr.s
class CoreCrudClient(BaseCoreClient):
    """Client for core endpoints defined by stac."""

    @staticmethod
    def _get_base_url(request):
        headers = request.headers
        # check if deployed behind a proxy - currently API Gateway
        if "x-amzn-apigateway-api-id" not in headers.keys():
            return str(request.base_url)
        else:
            apigateway_id = request.headers["x-amzn-apigateway-api-id"]
            aws_region=settings.aws_region
            deployment_stage=settings.deployment_stage
            return f"https://{apigateway_id}.execute-api.{aws_region}.amazonaws.com/{deployment_stage}/"

    async def landing_page(self, **kwargs) -> ORJSONResponse:
        """Landing page.

        Called with `GET /`.

        Returns:
            API landing page, serving as an entry point to the API.
        """
        request = kwargs["request"]
        base_url = CoreCrudClient._get_base_url(request)
        request._url = base_url
        landing_page = LandingPage(
            title="Arturo STAC API",
            description="Arturo raster datastore",
            links=[
                Link(
                    rel=Relations.self,
                    type=MimeTypes.json,
                    href=str(base_url),
                ),
                Link(
                    rel=Relations.docs,
                    type=MimeTypes.html,
                    title="OpenAPI docs",
                    href=urljoin(base_url, "docs"),
                ),
                Link(
                    rel=Relations.conformance,
                    type=MimeTypes.json,
                    title="STAC/WFS3 conformance classes implemented by this server",
                    href=urljoin(base_url, "conformance"),
                ),
                Link(
                    rel=Relations.search,
                    type=MimeTypes.geojson,
                    title="STAC search",
                    href=urljoin(base_url, "search"),
                ),
                Link(
                    rel="data",
                    type=MimeTypes.json,
                    href=urljoin(base_url, "collections"),
                ),
            ],
        )
        collections = await self._all_collections_func(request=request)
        if collections:
            for coll in collections:
                coll_link = CollectionLinks(
                    collection_id=coll.id, request=request
                ).link_self()
                coll_link.rel = Relations.child
                coll_link.title = coll.title
                landing_page.links.append(coll_link)
        return ORJSONResponse(landing_page.dict(exclude_none=True))

    async def conformance(self, **kwargs) -> ConformanceClasses:
        """Conformance classes."""
        return ConformanceClasses(
            conformsTo=[
                "https://stacspec.org/STAC-api.html",
                "http://docs.opengeospatial.org/is/17-069r3/17-069r3.html#ats_geojson",
            ]
        )

    async def _all_collections_func(self, **kwargs) -> List[Dict]:
        """Read all collections from the database."""
        request = kwargs["request"]
        request._url = CoreCrudClient._get_base_url(request)
        pool = request.app.state.readpool

        async with pool.acquire() as conn:
            collections = await conn.fetchval(
                """
                SELECT * FROM all_collections();
                """
            )
        linked_collections = []
        if collections is not None and len(collections) > 0:
            for c in collections:
                coll = Collection.construct(**c)
                coll.links = await CollectionLinks(
                    collection_id=coll.id, request=request
                ).get_links()
                linked_collections.append(coll)
        return linked_collections

    async def all_collections(self, **kwargs) -> ORJSONResponse:
        """Get all collections."""
        collections = await self._all_collections_func(**kwargs)
        if collections is None or len(collections) < 1:
            return ORJSONResponse([])
        return ORJSONResponse([c.dict(exclude_none=True) for c in collections])

    async def get_collection(self, id: str, **kwargs) -> ORJSONResponse:
        """Get collection by id.

        Called with `GET /collections/{collectionId}`.

        Args:
            id: Id of the collection.

        Returns:
            Collection.
        """
        request = kwargs["request"]
        request._url = CoreCrudClient._get_base_url(request)
        pool = kwargs["request"].app.state.readpool
        async with pool.acquire() as conn:
            q, p = render(
                """
                SELECT * FROM get_collection(:id::text);
                """,
                id=id,
            )
            collection = await conn.fetchval(q, *p)
        if collection is None:
            raise NotFoundError
        links = await CollectionLinks(collection_id=id, request=request).get_links()
        collection["links"] = links
        return ORJSONResponse(
            Collection.construct(**collection).dict(exclude_none=True)
        )

    async def _search_base(
        self, search_request: PgstacSearch, **kwargs
    ) -> Dict[str, Any]:
        """Cross catalog search (POST).

        Called with `POST /search`.

        Args:
            search_request: search request parameters.

        Returns:
            ItemCollection containing items which match the search criteria.
        """
        request = kwargs["request"]
        request._url = CoreCrudClient._get_base_url(request)
        pool = request.app.state.readpool

        # pool = kwargs["request"].app.state.readpool
        req = search_request.json(exclude_none=True)

        async with pool.acquire() as conn:
            q, p = render(
                """
                SELECT * FROM search(:req::text::jsonb);
                """,
                req=req,
            )
            items = await conn.fetchval(q, *p)
        next = items.pop("next", None)
        prev = items.pop("prev", None)
        collection = ItemCollection.construct(**items)
        cleaned_features = []
        if collection.features is None or len(collection.features) == 0:
            raise NotFoundError("No features found")

        for feature in collection.features:
            feature = Item.construct(**feature)
            if "links" not in search_request.fields.exclude:
                links = await ItemLinks(
                    collection_id=feature.collection,
                    item_id=feature.id,
                    request=request,
                ).get_links()
                feature.links = links
                exclude = search_request.fields.exclude
                if len(exclude) == 0:
                    exclude = None
                include = search_request.fields.include
                if len(include) == 0:
                    include = None
                feature = feature.dict(
                    exclude_none=True,
                )
            cleaned_features.append(feature)
            collection.features = cleaned_features
        collection.links = await PagingLinks(
            request=request,
            next=next,
            prev=prev,
        ).get_links()
        return collection

    async def item_collection(
        self, id: str, limit: int = 10, token: str = None, **kwargs
    ) -> ORJSONResponse:
        """Get all items from a specific collection.

        Called with `GET /collections/{collectionId}/items`

        Args:
            id: id of the collection.
            limit: number of items to return.
            token: pagination token.

        Returns:
            An ItemCollection.
        """
        req = PgstacSearch(collections=[id], limit=limit, token=token)
        collection = await self._search_base(req, **kwargs)
        links = await CollectionLinks(
            collection_id=id, request=kwargs["request"]
        ).get_links(extra_links=collection.links)
        collection.links = links
        return ORJSONResponse(collection.dict(exclude_none=True))

    async def get_item(
        self, item_id: str, collection_id: str, **kwargs
    ) -> ORJSONResponse:
        """Get item by id.

        Called with `GET /collections/{collectionId}/items/{itemId}`.

        Args:
            id: Id of the item.

        Returns:
            Item.
        """
        req = PgstacSearch(ids=[item_id], limit=1)
        collection = await self._search_base(req, **kwargs)
        return ORJSONResponse(collection.features[0])

    async def post_search(
        self, search_request: PgstacSearch, **kwargs
    ) -> ORJSONResponse:
        """Cross catalog search (POST).

        Called with `POST /search`.

        Args:
            search_request: search request parameters.

        Returns:
            ItemCollection containing items which match the search criteria.
        """
        collection = await self._search_base(search_request, **kwargs)
        return ORJSONResponse(collection.dict(exclude_none=True))

    async def get_search(
        self,
        collections: Optional[List[str]] = None,
        ids: Optional[List[str]] = None,
        bbox: Optional[List[NumType]] = None,
        datetime: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = 10,
        query: Optional[str] = None,
        token: Optional[str] = None,
        fields: Optional[List[str]] = None,
        sortby: Optional[str] = None,
        **kwargs,
    ) -> ORJSONResponse:
        """Cross catalog search (GET).

        Called with `GET /search`.

        Returns:
            ItemCollection containing items which match the search criteria.
        """
        # Parse request parameters
        base_args = {
            "collections": collections,
            "ids": ids,
            "bbox": bbox,
            "limit": limit,
            "token": token,
            "query": orjson.loads(query) if query else query,
        }
        if datetime:
            base_args["datetime"] = datetime

        if sortby:
            # https://github.com/radiantearth/stac-spec/tree/master/api-spec/extensions/sort#http-get-or-post-form
            sort_param = []
            for sort in sortby:
                sortparts = re.match(r"^([+-]?)(.*)$", sort)

                sort_param.append(
                    {
                        "field": sortparts.group(2).strip(),
                        "direction": "desc" if sortparts.group(1) == "-" else "asc",
                    }
                )
            base_args["sortby"] = sort_param

        if fields:
            includes = set()
            excludes = set()
            for field in fields:
                if field[0] == "-":
                    excludes.add(field[1:])
                elif field[0] == "+":
                    includes.add(field[1:])
                else:
                    includes.add(field)
            base_args["fields"] = {"include": includes, "exclude": excludes}

        # Do the request
        search_request = PgstacSearch(**base_args)
        return await self.post_search(search_request, request=kwargs["request"])
