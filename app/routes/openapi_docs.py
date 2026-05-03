"""OpenAPI document and Swagger UI (no extra runtime deps; UI assets from CDN)."""

from flask import Blueprint, Response, jsonify, request

from app.openapi_spec import build_openapi_dict

openapi_docs_bp = Blueprint("openapi_docs", __name__)


@openapi_docs_bp.route("/openapi.json", methods=["GET"])
def openapi_json():
    """Machine-readable OpenAPI 3.0 schema."""
    return jsonify(build_openapi_dict())


@openapi_docs_bp.route("/docs", methods=["GET"])
def swagger_ui():
    """Interactive API explorer; loads spec from ``/api/openapi.json`` on this host."""
    spec_url = f"{request.url_root.rstrip('/')}/api/openapi.json"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>LA-Server API — Swagger UI</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui.min.css" crossorigin="anonymous"/>
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui-bundle.min.js" crossorigin="anonymous"></script>
<script>
  window.onload = () => {{
    SwaggerUIBundle({{
      url: {spec_url!r},
      dom_id: "#swagger-ui",
      persistAuthorization: true,
    }});
  }};
</script>
</body>
</html>"""
    return Response(html, mimetype="text/html; charset=utf-8")
