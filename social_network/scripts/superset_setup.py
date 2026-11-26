import http.cookiejar
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = os.environ.get("SUPERSET_BASE_URL", "http://localhost:8088")
ADMIN_USER = os.environ["SUPERSET_ADMIN_USER"]
ADMIN_PASSWORD = os.environ["SUPERSET_ADMIN_PASSWORD"]
DATABASE_NAME = "Vertica Social"

DATASETS = [
    ("marts", "dm_person_activity"),
    ("marts", "dm_group_activity"),
    ("marts", "dm_message_stats"),
    ("sys_marts", "sys_cron_schedule"),
    ("sys_marts", "sys_task_runs"),
]


def metric(column, label):
    return {
        "expressionType": "SIMPLE",
        "aggregate": "SUM",
        "column": {"column_name": column},
        "label": label,
    }


CHARTS = [
    {
        "slice_name": "Отправленные и полученные сообщения",
        "datasource": "dm_person_activity",
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["person_id"],
            "metrics": [
                metric("messages_sent", "Отправлено"),
                metric("messages_received", "Получено"),
            ],
            "order_desc": True,
            "row_limit": 50,
            "y_axis_format": "SMART_NUMBER",
        },
    },
    {
        "slice_name": "Сообщения по группам",
        "datasource": "dm_group_activity",
        "viz_type": "dist_bar",
        "params": {
            "groupby": ["group_id"],
            "metrics": [metric("messages_count", "Сообщений")],
            "order_desc": True,
            "row_limit": 50,
            "y_axis_format": "SMART_NUMBER",
        },
    },
    {
        "slice_name": "Состав групп",
        "datasource": "dm_group_activity",
        "viz_type": "table",
        "params": {
            "columns": ["group_id", "title", "owner_id", "messages_count", "members_count"],
            "metrics": [],
            "row_limit": 100,
        },
    },
    {
        "slice_name": "Динамика сообщений по дням",
        "datasource": "dm_message_stats",
        "viz_type": "echarts_timeseries_line",
        "params": {
            "x_axis": "stat_date",
            "metrics": [
                metric("messages_total", "Всего"),
                metric("group_messages", "В группы"),
                metric("messages_with_link", "Со ссылкой"),
            ],
            "row_limit": 100,
        },
    },
    {
        "slice_name": "CRON-расписания задач",
        "datasource": "sys_cron_schedule",
        "viz_type": "table",
        "params": {
            "columns": [
                "dag_id",
                "task_id",
                "cron_expression",
                "is_valid_cron",
                "has_schedule",
                "next_fire_time",
            ],
            "metrics": [],
            "row_limit": 100,
        },
    },
    {
        "slice_name": "Статусы выполнения задач",
        "datasource": "sys_task_runs",
        "viz_type": "table",
        "params": {
            "columns": ["dag_id", "task_id", "state", "start_date", "duration_sec", "try_number"],
            "metrics": [],
            "row_limit": 100,
        },
    },
]

ANALYTICS_ROWS = [
    [("Отправленные и полученные сообщения", 6), ("Динамика сообщений по дням", 6)],
    [("Сообщения по группам", 6), ("Состав групп", 6)],
]

ADMIN_ROWS = [
    [("CRON-расписания задач", 12)],
    [("Статусы выполнения задач", 12)],
]

DASHBOARDS = [
    ("social-analytics", "Аналитика соцсети", ANALYTICS_ROWS),
    ("process-administration", "Администрирование процессов", ADMIN_ROWS),
]


def make_session():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def login(opener):
    page = opener.open(BASE_URL + "/login/").read().decode()
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page)
    if match is None:
        raise RuntimeError("login page has no csrf token")
    form = urllib.parse.urlencode(
        {"username": ADMIN_USER, "password": ADMIN_PASSWORD, "csrf_token": match.group(1)}
    ).encode()
    with opener.open(BASE_URL + "/login/", form) as response:
        if response.url.endswith("/login/"):
            raise RuntimeError("login failed: redirected back to login page")
    body = json.loads(opener.open(BASE_URL + "/api/v1/security/csrf_token/").read())
    return body["result"]


def api(opener, method, path, payload=None, csrf=None):
    headers = {"Accept": "application/json", "Referer": BASE_URL + "/"}
    if csrf is not None:
        headers["X-CSRFToken"] = csrf
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers=headers,
    )
    try:
        with opener.open(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def find_one(opener, path, field, value, csrf):
    _, body = api(opener, "GET", f"{path}?q=(page_size:100)", csrf=csrf)
    for item in body.get("result", []):
        if item.get(field) == value:
            return item["id"]
    return None


def ensure_dataset(opener, csrf, schema, table, database_id):
    existing = find_one(opener, "/api/v1/dataset/", "table_name", table, csrf)
    if existing:
        return existing
    payload = {"database": database_id, "schema": schema, "table_name": table}
    status, body = api(opener, "POST", "/api/v1/dataset/", payload, csrf=csrf)
    if status != 201:
        raise RuntimeError(f"dataset {table} failed: {status} {body}")
    return body["id"]


def build_query_context(datasource_id, spec):
    params = spec["params"]
    query = {
        "columns": params.get("columns", []),
        "metrics": params.get("metrics", []),
        "groupby": params.get("groupby", []),
        "orderby": [],
        "annotation_layers": [],
        "row_limit": params.get("row_limit", 100),
        "timeseries_limit": 0,
        "order_desc": params.get("order_desc", True),
        "url_params": {},
        "custom_params": {},
        "custom_form_data": {},
    }
    return {
        "datasource": {"id": datasource_id, "type": "table"},
        "queries": [query],
        "form_data": {"datasource": f"{datasource_id}__table", "viz_type": spec["viz_type"], **params},
        "result_format": "json",
        "result_type": "full",
    }


def ensure_chart(opener, csrf, spec, datasets):
    existing = find_one(opener, "/api/v1/chart/", "slice_name", spec["slice_name"], csrf)
    datasource_id = datasets[spec["datasource"]]
    params = {"datasource": f"{datasource_id}__table", "viz_type": spec["viz_type"], **spec["params"]}
    query_context = build_query_context(datasource_id, spec)
    if existing:
        payload = {"params": json.dumps(params), "query_context": json.dumps(query_context)}
        status, body = api(opener, "PUT", f"/api/v1/chart/{existing}", payload, csrf=csrf)
        if status != 200:
            raise RuntimeError(f"chart {spec['slice_name']} update failed: {status} {body}")
        return existing
    payload = {
        "slice_name": spec["slice_name"],
        "viz_type": spec["viz_type"],
        "datasource_id": datasource_id,
        "datasource_type": "table",
        "params": json.dumps(params),
        "query_context": json.dumps(query_context),
    }
    status, body = api(opener, "POST", "/api/v1/chart/", payload, csrf=csrf)
    if status != 201:
        raise RuntimeError(f"chart {spec['slice_name']} failed: {status} {body}")
    return body["id"]


def build_positions(rows, chart_ids):
    row_ids = []
    positions = {}
    for index, row in enumerate(rows, start=1):
        row_id = f"ROW-{index}"
        row_ids.append(row_id)
        chart_nodes = []
        for chart_index, (name, width) in enumerate(row, start=1):
            node_id = f"CHART-{index}-{chart_index}"
            chart_nodes.append(node_id)
            positions[node_id] = {
                "type": "CHART",
                "id": node_id,
                "parentId": row_id,
                "children": [],
                "meta": {"chartId": chart_ids[name], "width": width, "height": 50, "sliceName": name},
            }
        positions[row_id] = {
            "type": "ROW",
            "id": row_id,
            "parentId": "GRID_ID",
            "children": chart_nodes,
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
    positions["ROOT_ID"] = {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]}
    positions["GRID_ID"] = {"type": "GRID", "id": "GRID_ID", "parentId": "ROOT_ID", "children": row_ids}
    return positions


def ensure_dashboard(opener, csrf, slug, title, layout, chart_ids):
    dashboard_id = find_one(opener, "/api/v1/dashboard/", "slug", slug, csrf)
    if dashboard_id is None:
        status, body = api(
            opener,
            "POST",
            "/api/v1/dashboard/",
            {"dashboard_title": title, "slug": slug},
            csrf=csrf,
        )
        if status != 201:
            raise RuntimeError(f"dashboard {slug} failed: {status} {body}")
        dashboard_id = body["id"]
    charts = [{"id": chart_ids[name]} for row in layout for name, _ in row]
    add_charts = {"dashboard_id": dashboard_id, "charts": charts}
    api(opener, "POST", f"/api/v1/dashboard/{dashboard_id}/charts", add_charts, csrf=csrf)
    positions = build_positions(layout, chart_ids)
    payload = {"position_json": json.dumps(positions)}
    status, body = api(opener, "PUT", f"/api/v1/dashboard/{dashboard_id}", payload, csrf=csrf)
    if status != 200:
        raise RuntimeError(f"dashboard {slug} layout failed: {status} {body}")
    for row in layout:
        for name, _ in row:
            chart_id = chart_ids[name]
        status, body = api(opener, "PUT", f"/api/v1/chart/{chart_id}", {"dashboards": [dashboard_id]}, csrf=csrf)
        if status != 200:
            raise RuntimeError(f"chart {chart_id} link failed: {status} {body}")
    return dashboard_id


def main():
    opener = make_session()
    csrf = login(opener)
    _, body = api(opener, "GET", "/api/v1/database/", csrf=csrf)
    database_id = next(item["id"] for item in body["result"] if item["database_name"] == DATABASE_NAME)

    datasets = {}
    for schema, table in DATASETS:
        datasets[table] = ensure_dataset(opener, csrf, schema, table, database_id)
        print(f"dataset {schema}.{table} -> {datasets[table]}")

    chart_ids = {}
    for spec in CHARTS:
        chart_ids[spec["slice_name"]] = ensure_chart(opener, csrf, spec, datasets)
        print(f"chart {spec['slice_name']} -> {chart_ids[spec['slice_name']]}")

    for slug, title, layout in DASHBOARDS:
        dashboard_id = ensure_dashboard(opener, csrf, slug, title, layout, chart_ids)
        print(f"dashboard {slug} -> {dashboard_id}")


if __name__ == "__main__":
    main()
