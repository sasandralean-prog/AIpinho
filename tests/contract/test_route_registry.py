from collections import Counter

from aipinho.app_factory import create_app
from aipinho.registries.route_registry import RouteRegistry


def test_minimum_routes_exist():
    app = create_app()
    routes = RouteRegistry().list_routes(app)
    route_keys = {(method, item["path"]) for item in routes for method in item["methods"]}

    assert ("GET", "/api/v1/health") in route_keys
    assert ("GET", "/api/v1/status") in route_keys
    assert ("GET", "/api/v1/config/status") in route_keys
    assert ("GET", "/api/v1/policy/status") in route_keys
    assert ("GET", "/api/v1/policy/actions") in route_keys
    assert ("GET", "/api/v1/policy/precedence") in route_keys
    assert ("GET", "/api/v1/roles") in route_keys
    assert ("GET", "/api/v1/routes") in route_keys
    assert ("POST", "/api/v1/previews") in route_keys
    assert ("GET", "/api/v1/previews/{preview_id}") in route_keys
    assert ("POST", "/api/v1/previews/from-draft/{draft_id}") in route_keys
    assert ("POST", "/api/v1/approvals") in route_keys
    assert ("POST", "/api/v1/approvals/{approval_id}/approve") in route_keys
    assert ("POST", "/api/v1/approvals/{approval_id}/reject") in route_keys
    assert ("POST", "/api/v1/approvals/{approval_id}/cancel") in route_keys
    assert ("GET", "/api/v1/tools") in route_keys
    assert ("GET", "/api/v1/tools/status") in route_keys
    assert ("GET", "/api/v1/tools/catalog") in route_keys
    assert ("POST", "/api/v1/tools/invocation/preview") in route_keys
    assert ("POST", "/api/v1/tools/validate") in route_keys
    assert ("POST", "/api/v1/tools/preview") in route_keys
    assert ("POST", "/api/v1/tools/dry-run") in route_keys
    assert ("POST", "/api/v1/tools/dry-run/from-preview/{preview_id}") in route_keys
    assert ("POST", "/api/v1/tools/dry-run/from-draft/{draft_id}") in route_keys
    assert ("GET", "/api/v1/tools/execution-status") in route_keys
    assert ("POST", "/api/v1/tools/execute-readonly") in route_keys
    assert ("POST", "/api/v1/tools/execute-readonly/from-preview/{preview_id}") in route_keys
    assert ("POST", "/api/v1/tools/execute-readonly/from-draft/{draft_id}") in route_keys
    assert ("GET", "/api/v1/tools/executions/{execution_id}") in route_keys
    assert ("GET", "/api/v1/tools/executions/{execution_id}/events") in route_keys
    assert ("GET", "/api/v1/tool-registry/catalog") in route_keys
    assert ("GET", "/api/v1/agent-tool-gateway/tools") in route_keys


def test_public_tools_routes_have_single_owner():
    app = create_app()
    routes = RouteRegistry().list_routes(app)
    route_keys = [
        (method, item["path"])
        for item in routes
        for method in item["methods"]
        if item["path"] in {"/api/v1/tools", "/api/v1/tools/status", "/api/v1/tools/{tool_id}"}
    ]

    counts = Counter(route_keys)
    assert counts[("GET", "/api/v1/tools")] == 1
    assert counts[("GET", "/api/v1/tools/status")] == 1
    assert counts[("GET", "/api/v1/tools/{tool_id}")] == 1


def test_no_destructive_runtime_routes_are_registered():
    app = create_app()
    paths = {item["path"] for item in RouteRegistry().list_routes(app)}

    assert "/api/v1/tools/execute" not in paths
    assert "/api/v1/patch/apply" not in paths
    assert all(path.startswith("/api/v1") for path in paths)
