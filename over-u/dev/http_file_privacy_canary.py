"""Run HTTP-only homework-file upload and authorization checks against CI Frappe."""

import http.cookiejar
import json
import os
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener

BASE = "http://over-u.localhost:8000"
SENTINEL = b"OVER_U_SYNTHETIC_HTTP_UPLOAD"
PASS = os.environ["OVER_U_DEMO_PASSWORD"]
ADMIN_PASS = os.environ["OVER_U_ADMIN_PASSWORD"]
UPLOAD_PROBE = json.loads(os.environ["OVER_U_UPLOAD_PROBE"])
FILE_FIELDS = [
	"name",
	"owner",
	"file_url",
	"is_private",
	"attached_to_doctype",
	"attached_to_name",
	"attached_to_field",
]


class NoRedirect(HTTPRedirectHandler):
	def redirect_request(self, request, response, code, message, headers, new_url):
		return None


def client():
	return build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()), NoRedirect)


def request(client_, path, data=None, headers=None):
	try:
		with client_.open(Request(BASE + path, data=data, headers=headers or {}), timeout=30) as response:
			return response.status, response.read(), response.headers
	except HTTPError as error:
		return error.code, error.read(), error.headers
	except URLError as error:
		raise AssertionError(f"HTTP request failed for {path}: {error}") from error


def api(client_, method, params, http_method="POST"):
	encoded = urlencode(
		{key: json.dumps(value) if isinstance(value, dict | list) else value for key, value in params.items()}
	)
	if http_method == "GET":
		status, body, _headers = request(client_, f"/api/method/{method}?{encoded}")
	else:
		status, body, _headers = request(
			client_,
			f"/api/method/{method}",
			encoded.encode(),
			{"Content-Type": "application/x-www-form-urlencoded"},
		)
	try:
		return status, json.loads(body)
	except json.JSONDecodeError:
		return status, {"raw": body.decode("utf-8", "replace")}


def probe_identity(client_):
	status, session = api(client_, "frappe.auth.get_logged_user", {}, http_method="GET")
	actual = session.get("message") if isinstance(session, dict) else None
	return {"http": status, "identity": actual}


def cookie_metadata(client_):
	processor = next(handler for handler in client_.handlers if isinstance(handler, HTTPCookieProcessor))
	return [
		{
			"name": cookie.name,
			"domain": cookie.domain,
			"path": cookie.path,
			"secure": cookie.secure,
			"expires": cookie.expires,
		}
		for cookie in processor.cookiejar
	]


def assert_identity(client_, expected):
	probe = probe_identity(client_)
	assert probe == {"http": 200, "identity": expected}, (
		f"Session identity mismatch: expected={expected!r}, "
		f"status={probe['http']}, actual={probe['identity']!r}"
	)
	return probe


def checkpoint(label, client_):
	probe = probe_identity(client_)
	detail = {"stage": label, "probe": probe}
	if probe["http"] != 200:
		detail["cookie_metadata"] = cookie_metadata(client_)
	print("Owner session checkpoint:", json.dumps(detail, sort_keys=True))
	return probe


def login(email, password=PASS):
	client_ = client()
	status, payload = api(client_, "login", {"usr": email, "pwd": password})
	assert status == 200, f"Synthetic login failed: user label={email.split('@')[0]}, HTTP {status}"
	assert_identity(client_, email)
	return client_


def multipart(fields, filename, content):
	boundary = "----over-u-" + uuid.uuid4().hex
	parts = []
	for name, value in fields.items():
		parts.extend(
			[
				f"--{boundary}\r\n".encode(),
				f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
				str(value).encode(),
				b"\r\n",
			]
		)
	parts.extend(
		[
			f"--{boundary}\r\n".encode(),
			f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
			b"Content-Type: text/plain\r\n\r\n",
			content,
			b"\r\n",
			f"--{boundary}--\r\n".encode(),
		]
	)
	return boundary, b"".join(parts)


def message(payload):
	value = payload.get("message") if isinstance(payload, dict) else None
	return value if isinstance(value, dict) else {}


def rows(payload):
	value = payload.get("message") if isinstance(payload, dict) else None
	return value if isinstance(value, list) else []


def has_sentinel(body):
	return SENTINEL in body


def main():
	student_email = UPLOAD_PROBE["student"]
	owner = login(student_email)
	filename = "over-u-http-private-attachment.txt"
	boundary, body = multipart(
		{
			"doctype": "",
			"docname": "",
			"fieldname": "",
			"folder": "Home",
			"is_private": "1",
			"file_url": "",
			"file_name": filename,
			"total_file_size": len(SENTINEL),
			"optimize": "0",
		},
		filename,
		SENTINEL,
	)
	status, uploaded_body, _headers = request(
		owner,
		"/api/method/upload_file",
		body,
		{"Content-Type": f"multipart/form-data; boundary={boundary}"},
	)
	if status != 200:
		try:
			upload_error = json.loads(uploaded_body)
		except json.JSONDecodeError:
			upload_error = {}
		detail = {
			"exc_type": upload_error.get("exc_type"),
			"message": upload_error.get("message"),
		}
		raise AssertionError(
			f"Normal standalone private upload failed: HTTP {status}, "
			f"server_error={json.dumps(detail, sort_keys=True)}"
		)
	uploaded = message(json.loads(uploaded_body))
	owner_after_upload = checkpoint("after_standalone_upload", owner)
	file_url, file_name = uploaded.get("file_url"), uploaded.get("name")
	assert int(uploaded.get("is_private") or 0) == 1, "Normal LMS upload was not private"
	assert file_url and file_url.startswith("/private/files/"), "Normal LMS upload was not stored privately"
	assert uploaded.get("owner") == student_email, "Uploaded File owner did not match the learner"
	assert not uploaded.get("attached_to_doctype") and not uploaded.get(
		"attached_to_name"
	), "Standalone LMS upload unexpectedly attached the file before submission creation"

	status, inserted = api(
		owner,
		"frappe.client.insert",
		{
			"doc": {
				"doctype": "LMS Assignment Submission",
				"assignment": UPLOAD_PROBE["assignment"],
				"member": student_email,
				"type": "PDF",
				"assignment_attachment": file_url,
			},
		},
	)
	assert status == 200, f"Normal student submission insert failed: HTTP {status}"
	submission_name = message(inserted).get("name")
	assert submission_name, "Normal student insert returned no submission name"
	owner_after_insert = checkpoint("after_submission_insert", owner)

	# Re-authenticate after the standard upload/insert flow, then identify the session
	# immediately before reopening the learner's own submission.
	owner = login(student_email)
	checkpoint("before_submission_reopen", owner)
	status, reopened = api(
		owner,
		"frappe.client.get",
		{"doctype": "LMS Assignment Submission", "name": submission_name},
	)
	owner_submission_open = status == 200 and message(reopened).get("assignment_attachment") == file_url
	read_error = reopened if isinstance(reopened, dict) else {}
	print(
		"Owner submission HTTP get:",
		json.dumps(
			{
				"status": status,
				"exc_type": read_error.get("exc_type"),
				"message": read_error.get("message"),
				"attachment_matches": owner_submission_open,
			},
			sort_keys=True,
		),
	)
	owner_after_reopen = checkpoint("after_submission_reopen", owner)
	if not owner_submission_open:
		# A permission error may clear the failed request's session cookie. Start a
		# fresh owner session so file authorization is measured independently.
		owner = login(student_email)


	admin = login("Administrator", ADMIN_PASS)
	admin_status, admin_submission = api(
		admin,
		"frappe.client.get",
		{"doctype": "LMS Assignment Submission", "name": submission_name},
	)
	admin_submission_facts = message(admin_submission)
	print(
		"Admin synthetic submission facts:",
		json.dumps(
			{
				"status": admin_status,
				"name": admin_submission_facts.get("name"),
				"owner": admin_submission_facts.get("owner"),
				"member": admin_submission_facts.get("member"),
				"assignment": admin_submission_facts.get("assignment"),
				"assignment_attachment": admin_submission_facts.get("assignment_attachment"),
			},
			sort_keys=True,
		),
	)


	status, same_url_payload = api(
		admin,
		"frappe.client.get_list",
		{
			"doctype": "File",
			"filters": {"file_url": file_url},
			"fields": FILE_FIELDS,
			"limit_page_length": 100,
		},
	)
	duplicate_rows = rows(same_url_payload) if status == 200 else []
	duplicate_rows = [{key: row.get(key) for key in FILE_FIELDS} for row in duplicate_rows]
	assert (
		len(duplicate_rows) == 1
	), f"Expected exactly one synthetic File row for the uploaded URL, got {len(duplicate_rows)}"
	file_row = duplicate_rows[0]
	assert (
		file_row.get("owner") == student_email
		and int(file_row.get("is_private") or 0) == 1
		and file_row.get("attached_to_doctype") == "LMS Assignment Submission"
		and file_row.get("attached_to_name") == submission_name
		and file_row.get("attached_to_field") == "assignment_attachment"
	), "Saved assignment did not own a correctly linked private File row"

	clients = {
		"owner": (owner, student_email),
		"other student": (login("student2@over-u.example.com"), "student2@over-u.example.com"),
		"assigned teacher": (login("teacher@over-u.example.com"), "teacher@over-u.example.com"),
		"unrelated Course Creator": (
			login("over-u-unrelated-teacher@example.com"),
			"over-u-unrelated-teacher@example.com",
		),
	}
	guest = client()
	actors = [(label, *entry) for label, entry in clients.items()]
	actors.append(("Guest", guest, "Guest"))
	public_path = "/files/" + file_url.rsplit("/", 1)[-1]
	results = {}
	session_violations = []

	for label, session, identity in actors:
		# Probe after setup and immediately before each file route. A failing probe
		# is recorded but must not prevent collecting the actual download response.
		identity_checks = []
		for route_name, route in (
			("plain_url", lambda: request(session, file_url)),
			("plain_url_with_fid", lambda: request(session, file_url + "?" + urlencode({"fid": file_name}))),
			(
				"handler_download_file",
				lambda: request(
					session,
					"/api/method/frappe.handler.download_file?"
					+ urlencode({"file_url": file_url, "fid": file_name}),
				),
			),
			("public_files_url", lambda: request(session, public_path)),
		):
			probe = {"http": None, "identity": "Guest"} if label == "Guest" else probe_identity(session)
			identity_checks.append({"before": route_name, **probe})
			if label != "Guest" and probe != {"http": 200, "identity": identity}:
				detail = {"actor": label, "before": route_name, "probe": probe}
				session_violations.append(json.dumps(detail, sort_keys=True))
				print(
					"Session probe failure:",
					json.dumps(
						{
							**detail,
							"cookie_metadata": cookie_metadata(session),
						},
						sort_keys=True,
					),
				)
			status, body, _headers = route()
			if route_name == "plain_url":
				plain_status, plain_body = status, body
			elif route_name == "plain_url_with_fid":
				fid_status, fid_body = status, body
			elif route_name == "handler_download_file":
				handler_status, handler_body = status, body
			else:
				public_status, public_body = status, body

		file_status, file_payload = api(session, "frappe.client.get", {"doctype": "File", "name": file_name})
		file_record = message(file_payload)
		file_visible = file_status == 200 and file_record.get("file_url") == file_url
		list_status, file_list_payload = api(
			session,
			"frappe.client.get_list",
			{
				"doctype": "File",
				"filters": {"file_url": file_url},
				"fields": FILE_FIELDS,
				"limit_page_length": 100,
			},
		)
		visible_rows = rows(file_list_payload)
		file_list_visible = any(row.get("name") == file_name for row in visible_rows)

		sub_status, sub_payload = api(
			session,
			"frappe.client.get",
			{"doctype": "LMS Assignment Submission", "name": submission_name},
		)
		sub_record = message(sub_payload)
		sub_visible = sub_status == 200 and sub_record.get("assignment_attachment") == file_url
		sub_list_status, sub_list_payload = api(
			session,
			"frappe.client.get_list",
			{
				"doctype": "LMS Assignment Submission",
				"filters": {"name": submission_name},
				"fields": ["name", "assignment_attachment"],
				"limit_page_length": 10,
			},
		)
		sub_rows = rows(sub_list_payload)
		sub_list_visible = any(row.get("name") == submission_name for row in sub_rows)
		private_results = {
			"identity_before_routes": identity_checks,
			"plain_url": (plain_status, has_sentinel(plain_body)),
			"plain_url_with_fid": (fid_status, has_sentinel(fid_body)),
			"handler_download_file": (handler_status, has_sentinel(handler_body)),
			"file_get": (file_status, file_visible),
			"file_get_list": (list_status, file_list_visible),
			"submission_get": (sub_status, sub_visible),
			"submission_get_list": (sub_list_status, sub_list_visible),
			"public_files_url": (public_status, has_sentinel(public_body)),
		}
		results[label] = private_results
	violations = list(session_violations)
	if not owner_submission_open:
		violations.append("owner submission attachment reference did not survive reopen")
	for label, method_results in results.items():
		allowed = label in ("owner", "assigned teacher")
		for method in ("plain_url", "plain_url_with_fid", "handler_download_file"):
			code, contains = method_results[method]
			if not ((code == 200 and contains) if allowed else (code != 200 and not contains)):
				violations.append(f"{label} {method}: HTTP {code}, sentinel={contains}")
		code, visible = method_results["file_get"]
		if visible != allowed:
			violations.append(f"{label} file_get: HTTP {code}, visible={visible}")
		code, visible = method_results["file_get_list"]
		if not allowed and visible:
			violations.append(f"{label} file_get_list exposed private File metadata: HTTP {code}")
		# Frappe 16's standard File query condition intentionally excludes linked
		# private files for non-System Users, including their owners. The attachment
		# field is the authorized user's path to the File record; do not widen the
		# global File list merely to make this canary return a row.
		for method in ("submission_get", "submission_get_list"):
			code, visible = method_results[method]
			if visible != allowed:
				violations.append(f"{label} {method}: HTTP {code}, visible={visible}")
		code, contains = method_results["public_files_url"]
		if code == 200 and contains:
			violations.append(f"{label} public_files_url exposed sentinel: HTTP {code}")

	print(
		"Synthetic upload metadata:",
		json.dumps({key: uploaded.get(key) for key in FILE_FIELDS}, sort_keys=True),
	)
	print("Same-URL File rows:", json.dumps(duplicate_rows, sort_keys=True))
	print(
		"Owner session checkpoints:",
		json.dumps(
			{
				"after_submission_insert": owner_after_insert,
				"after_upload_file": owner_after_upload,
				"after_submission_reopen": owner_after_reopen,
			},
			sort_keys=True,
		),
	)
	print("HTTP authorization matrix:", json.dumps(results, sort_keys=True))
	if len(duplicate_rows) != 1:
		violations.append(f"Ambiguous same-URL File count: {len(duplicate_rows)}")
	if violations:
		raise AssertionError("HTTP canary failures: " + " | ".join(violations))


if __name__ == "__main__":
	main()
