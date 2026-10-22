#!/usr/bin/env python3
"""Record normal local lab traffic. Do not submit grade/user/Ping forms or attacks."""
import csv
import hashlib
import http.cookiejar
import io
import json
import plistlib
import re
import subprocess
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, Request, build_opener
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8080"
COMPOSE = ["docker", "compose", "-p", "notesapp-lab", "-f", "docker-compose.yml", "-f", "compose.lab.yml"]


def command(args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def database_digest():
    # Only the digest leaves the database. All tables are synthetic course data.
    query = "SELECT md5(jsonb_build_object(" + ",".join(
        f"'{table}',(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM {table} t)"
        for table in ["users", "classes", "enrollments", "notes"]
    ) + ")::text)"
    return command(COMPOSE + ["exec", "-T", "db", "psql", "-U", "notesapp", "-d", "notesapp", "-tAc", query])


class Forms(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.active = None
        self.headings = []
        self.heading = None
        self.table_rows = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.active = {"action": attrs.get("action", ""), "method": attrs.get("method", "GET").upper(), "fields": []}
            self.forms.append(self.active)
        if tag in {"input", "select", "textarea"} and self.active is not None and attrs.get("name"):
            self.active["fields"].append(attrs["name"])
        if tag in {"h1", "h2"}:
            self.heading = ""
        if tag == "tr":
            self.table_rows += 1

    def handle_endtag(self, tag):
        if tag == "form":
            self.active = None
        if tag in {"h1", "h2"} and self.heading is not None:
            self.headings.append(self.heading.strip())
            self.heading = None

    def handle_data(self, data):
        if self.heading is not None:
            self.heading += data


class Redirects(HTTPRedirectHandler):
    def __init__(self):
        self.history = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.history.append({"from": urlsplit(req.full_url).path, "status": code, "to": urlsplit(newurl).path})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    def __init__(self, role, events):
        self.role = role
        self.events = events
        self.jar = http.cookiejar.CookieJar()
        self.redirects = Redirects()
        self.opener = build_opener(HTTPCookieProcessor(self.jar), self.redirects)

    def request(self, path, data=None, bearer=None):
        self.redirects.history = []
        cookie_present_before = bool(list(self.jar))
        headers = {"Authorization": "Bearer " + bearer} if bearer else {}
        encoded = urlencode(data).encode() if data is not None else None
        req = Request(BASE + path, data=encoded, headers=headers)
        try:
            response = self.opener.open(req, timeout=10)
        except HTTPError as error:
            response = error
        body = response.read().decode("utf-8")
        event = {"role": self.role, "method": req.get_method(), "path": path,
                 "status": response.status, "final_path": urlsplit(response.geturl()).path,
                 "redirects": list(self.redirects.history), "content_type": response.headers.get("Content-Type"),
                 "cookie_present_before": cookie_present_before, "bearer_sent": bool(bearer)}
        # Never save credentials, cookies, JWTs, or raw pages containing tokens.
        if "text/html" in (event["content_type"] or ""):
            parser = Forms()
            parser.feed(body)
            event.update({"headings": parser.headings, "forms": parser.forms, "table_rows_including_headers": parser.table_rows})
        elif "text/csv" in (event["content_type"] or ""):
            rows = list(csv.reader(io.StringIO(body)))
            event.update({"csv_columns": rows[0], "csv_data_rows": len(rows)-1,
                          "content_disposition": response.headers.get("Content-Disposition")})
        elif "application/json" in (event["content_type"] or ""):
            payload = json.loads(body)
            event["json_keys"] = sorted(payload)
        self.events.append(event)
        return body, event


def main():
    before = database_digest()
    events = []
    accounts = {}
    pattern = r"^\|\s*(Student|Teacher|Admin)\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`"
    for line in (ROOT / "README.md").read_text().splitlines():
        match = re.match(pattern, line)
        if match:
            accounts[match[1].lower()] = (match[2], match[3])
    assert set(accounts) == {"student", "teacher", "admin"}
    anon = Client("anonymous", events)
    for path in ["/", "/login", "/dashboard", "/teacher", "/admin", "/api/notes/1", "/healthz"]:
        anon.request(path)
    for role in ["student", "teacher", "admin"]:
        client = Client(role, events)
        client.request("/login")
        username, password = accounts[role]
        _, login = client.request("/login", {"username": username, "password": password})
        assert login["final_path"] == {"student": "/dashboard", "teacher": "/teacher", "admin": "/admin"}[role]
        dashboard = None
        for path in ["/", "/login", "/dashboard", "/teacher", "/admin", "/export.csv?class_id=1", "/static/style.css", "/healthz"]:
            body, event = client.request(path)
            if path == "/dashboard":
                dashboard = body
        if role == "student":
            token = json.loads(re.search(r"const TOKEN = (.+?);", dashboard).group(1))
            body, event = client.request("/api/notes/1", bearer=token)
            detail = json.loads(body)
            assert detail["student"] == username, "Only inspect this student's own seeded record"
            assert event["status"] == 200
            event["own_seeded_record"] = True
        _, logout = client.request("/logout")
        assert logout["final_path"] == "/login" and not list(client.jar)
    after = database_digest()
    assert before == after, "Observation must not change the course tables"
    routes_code = "import json; from app import app; print(json.dumps([{'path':str(r),'methods':sorted(set(r.methods)-{'HEAD','OPTIONS'})} for r in app.url_map.iter_rules()]))"
    routes = json.loads(command(COMPOSE + ["exec", "-T", "web", "python", "-c", routes_code]))
    desktop = plistlib.loads(Path("/Applications/Docker.app/Contents/Info.plist").read_bytes())
    result = {
        "observed_at": datetime.now(ZoneInfo("Europe/Paris")).isoformat(),
        "source_commit": command(["git", "rev-parse", "HEAD"]),
        "fork": "https://github.com/pursurer/NoteApp",
        "base_url": BASE,
        "docker_desktop": desktop.get("CFBundleShortVersionString"),
        "docker_engine": command(["docker", "version", "--format", "{{.Server.Version}}"]),
        "compose": command(["docker", "compose", "version", "--short"]),
        "postgres_image": json.loads(command(["docker", "image", "inspect", "postgres:15", "--format", "{{json .RepoDigests}}"])),
        "web_image_id": command(["docker", "image", "inspect", "notesapp-lab-web", "--format", "{{.Id}}"]),
        "database_before": before, "database_after": after, "database_unchanged": before == after,
        "route_map": routes, "events": events,
        "not_executed": ["POST /grades", "POST /admin/users", "POST /admin/ping", "attack payloads", "load tests"],
    }
    (ROOT / "lab" / "observations.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"normal_requests": len(events), "roles": ["anonymous", "student", "teacher", "admin"],
                      "database_unchanged": before == after, "routes": len(routes)}, indent=2))


if __name__ == "__main__":
    main()
