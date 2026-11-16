from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

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
    app = FastAPI(title='KPC API', version='0.1.0')

    @app.get('/api/health')
    def health():
        # Liveness only: this does not claim database/authentication readiness.
        return {'status': 'ok', 'service': 'kpc-api'}

    @app.api_route('/api/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
    def unknown_api(path: str):
        raise HTTPException(status_code=404, detail='API endpoint not found')

    if frontend_dist.is_dir():
        app.mount('/', SPAStaticFiles(directory=frontend_dist, html=True), name='frontend')

    return app


app = create_app()
