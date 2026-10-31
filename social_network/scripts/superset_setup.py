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

ANALYTICS_LAYOUT = [
    ("Отправленные и полученные сообщения", 6),
    ("Динамика сообщений по дням", 6),
    ("Сообщения по группам", 6),
    ("Состав групп", 6),
]

ADMIN_LAYOUT = [
    ("CRON-расписания задач", 12),
    ("Статусы выполнения задач", 12),
]

DASHBOARDS = [
    ("social-analytics", "Аналитика соцсети", ANALYTICS_LAYOUT),
    ("process-administration", "Администрирование процессов", ADMIN_LAYOUT),
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
    query = urllib.parse.quote(f"(filters:!((col:{field},opr:eq,value:{value})))")
    _, body = api(opener, "GET", f"{path}?q={query}", csrf=csrf)
    results = body.get("result", [])
    return results[0]["id"] if results else None


def ensure_dataset(opener, csrf, schema, table, database_id):
    existing = find_one(opener, "/api/v1/dataset/", "table_name", table, csrf)
    if existing:
        return existing
    payload = {"database": database_id, "schema": schema, "table_name": table}
    status, body = api(opener, "POST", "/api/v1/dataset/", payload, csrf=csrf)
    if status != 201:
        raise RuntimeError(f"dataset {table} failed: {status} {body}")
    return body["id"]


def ensure_chart(opener, csrf, spec, datasets):
    existing = find_one(opener, "/api/v1/chart/", "slice_name", spec["slice_name"], csrf)
    if existing:
        return existing
    datasource_id = datasets[spec["datasource"]]
    params = {"datasource": f"{datasource_id}__table", "viz_type": spec["viz_type"], **spec["params"]}
    payload = {
        "slice_name": spec["slice_name"],
        "viz_type": spec["viz_type"],
        "datasource_id": datasource_id,
        "datasource_type": "table",
        "params": json.dumps(params),
    }
    status, body = api(opener, "POST", "/api/v1/chart/", payload, csrf=csrf)
    if status != 201:
        raise RuntimeError(f"chart {spec['slice_name']} failed: {status} {body}")
    return body["id"]


def build_positions(layout, chart_ids):
    rows = []
    positions = {}
    for index, (name, width) in enumerate(layout, start=1):
        row_id = f"ROW-{index}"
        chart_id = f"CHART-{index}"
        rows.append(row_id)
        positions[row_id] = {
            "type": "ROW",
            "id": row_id,
            "parentId": "GRID_ID",
            "children": [chart_id],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        positions[chart_id] = {
            "type": "CHART",
            "id": chart_id,
            "parentId": row_id,
            "children": [],
            "meta": {"chartId": chart_ids[name], "width": width, "height": 50, "sliceName": name},
        }
    positions["ROOT_ID"] = {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]}
    positions["GRID_ID"] = {"type": "GRID", "id": "GRID_ID", "parentId": "ROOT_ID", "children": rows}
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
    charts = [{"id": chart_ids[name]} for name, _ in layout]
    add_charts = {"dashboard_id": dashboard_id, "charts": charts}
    api(opener, "POST", f"/api/v1/dashboard/{dashboard_id}/charts", add_charts, csrf=csrf)
    positions = build_positions(layout, chart_ids)
    api(opener, "PUT", f"/api/v1/dashboard/{dashboard_id}", {"positions": positions}, csrf=csrf)
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
