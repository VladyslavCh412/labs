"""Single public entrypoint; routes calls to independent FastAPI services."""
import os
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from gateway_routing import resolve_target

app = FastAPI(title='API Gateway — Автопарк ЛР3', version='1.0.0', description='Єдина точка входу до Fleet і Trips')
FLEET_URL = os.getenv('FLEET_URL', 'http://127.0.0.1:8101')
TRIPS_URL = os.getenv('TRIPS_URL', 'http://127.0.0.1:8102')

@app.get('/health')
async def health():
    return {'service': 'gateway', 'status': 'ok'}

@app.api_route('/{rest:path}', methods=['GET', 'POST', 'PATCH'])
async def proxy(rest: str, request: Request):
    target = resolve_target(rest, FLEET_URL, TRIPS_URL)
    if target is None:
        raise HTTPException(404, detail='unknown_endpoint')
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            res = await client.request(request.method, target.rstrip('/') + '/' + rest,
                                       content=await request.body(),
                                       headers={'Content-Type': request.headers.get('content-type', 'application/json'),
                                                'Authorization':request.headers.get('authorization','')})
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        raise HTTPException(503, detail='upstream_unavailable') from exc
    return Response(content=res.content, status_code=res.status_code,
                    media_type=res.headers.get('content-type', 'application/json'))
