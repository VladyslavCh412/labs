"""Local dashboard for the LR5 Fleet/Trips services.

The browser accesses only port 8000. The dashboard forwards requests to the
owning service via HTTP; it never accesses another service's SQLite database.
"""
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

FRONTEND = Path(__file__).resolve().parent / 'frontend'


def create_app(fleet_url=None, trips_url=None, transport=None):
    hosts = {
        'fleet': (fleet_url or os.getenv('FLEET_URL', 'http://127.0.0.1:8101')).rstrip('/'),
        'trips': (trips_url or os.getenv('TRIPS_URL', 'http://127.0.0.1:8102')).rstrip('/'),
    }
    app = FastAPI(title='FleetFlow — панель керування ЛР5', docs_url=None, redoc_url=None)
    app.mount('/assets', StaticFiles(directory=FRONTEND), name='assets')

    @app.get('/', include_in_schema=False)
    def home():
        return FileResponse(FRONTEND / 'index.html', media_type='text/html')

    @app.get('/api/health', include_in_schema=False)
    async def services_health():
        results = {}
        async with httpx.AsyncClient(timeout=2.5, transport=transport) as client:
            for service, root in hosts.items():
                try:
                    response = await client.get(root + '/health')
                    results[service] = response.status_code == 200 and response.json().get('status') == 'ok'
                except (httpx.HTTPError, ValueError):
                    results[service] = False
        return results

    @app.api_route('/api/{service}/{path:path}', methods=['GET', 'POST', 'PATCH'], include_in_schema=False)
    async def forward(service: str, path: str, request: Request):
        if service not in hosts or not path:
            raise HTTPException(404, 'unknown_service_or_endpoint')
        # The reverse proxy can only reach the two fixed localhost backends.
        destination = f"{hosts[service]}/{path}"
        if request.url.query:
            destination += '?' + request.url.query
        body = await request.body()
        try:
            async with httpx.AsyncClient(timeout=5.0, transport=transport) as client:
                response = await client.request(
                    method=request.method,
                    url=destination,
                    content=body if body else None,
                    headers={'content-type': request.headers.get('content-type', 'application/json')},
                )
        except httpx.HTTPError:
            return JSONResponse({'detail': f'{service}_unavailable'}, status_code=503)
        return Response(content=response.content, status_code=response.status_code,
                        media_type=response.headers.get('content-type', 'application/json'))

    return app


app = create_app()
