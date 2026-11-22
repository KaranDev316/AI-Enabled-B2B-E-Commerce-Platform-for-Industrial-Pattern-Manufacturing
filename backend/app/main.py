from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.production_issues import router as production_issues_router
from app.api.inventory import router as inventory_router
from app.api.production import router as production_router
from app.api.orders import router as orders_router
from app.api.invoices import router as invoices_router
from app.api.quotations import router as quotations_router
from app.api.catalogue_admin import router as catalogue_admin_router

from app.api import (
    admin_users_router,
    auth_router,
    portals_router,
    products_router,
    profile_router,
    rfqs_router,
    support_router,
)

FRONTEND_DIST = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and '.' not in Path(path).name:
                return await super().get_response('index.html', scope)
            raise


def create_app(frontend_dist: Path = FRONTEND_DIST) -> FastAPI:
    app = FastAPI(
        title='KPC API',
        description='Khodel Pattern Craft B2B Platform API',
        version='0.3.0',
    )

    @app.middleware('http')
    async def add_no_cache_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith('/api'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
        return response

    @app.get('/api/health')
    def health():
        # Liveness only: this does not claim database/authentication readiness.
        return {'status': 'ok', 'service': 'kpc-api'}

    # Include feature routers
    app.include_router(auth_router)
    app.include_router(profile_router)
    app.include_router(admin_users_router)
    app.include_router(products_router)
    app.include_router(catalogue_admin_router)
    app.include_router(rfqs_router)
    app.include_router(quotations_router)
    app.include_router(inventory_router)
    app.include_router(production_router)
    app.include_router(production_issues_router)
    app.include_router(orders_router)
    app.include_router(invoices_router)
    app.include_router(support_router)
    app.include_router(portals_router)

    # API 404 handler for unmatched /api routes
    @app.api_route('/api/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
    def unknown_api(path: str):
        raise HTTPException(status_code=404, detail='API endpoint not found')

    # Serve built SPA frontend if present
    if frontend_dist.is_dir():
        app.mount('/', SPAStaticFiles(directory=frontend_dist, html=True), name='frontend')

    return app


app = create_app()
