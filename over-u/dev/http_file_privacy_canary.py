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
FILE_FIELDS = ["name", "owner", "file_url", "is_private", "attached_to_doctype", "attached_to_name", "attached_to_field"]


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


def assert_identity(client_, expected):
	status, session = api(client_, "frappe.auth.get_logged_user", {})
	actual = session.get("message") if isinstance(session, dict) else None
	assert status == 200 and actual == expected, f"Session identity mismatch before request: expected={expected!r}, status={status}, actual={actual!r}"


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
	status, inserted = api(
		owner,
		"frappe.client.insert",
		{
			"doc": {
				"doctype": "LMS Assignment Submission",
				"assignment": UPLOAD_PROBE["assignment"],
				"member": student_email,
				"type": "Text",
				"answer": "Synthetic answer created through the ordinary student document API.",
			},
		},
	)
	assert status == 200, f"Normal student submission insert failed: HTTP {status}"
	submission_name = message(inserted).get("name")
	assert submission_name, "Normal student insert returned no submission name"

	filename = "over-u-http-private-attachment.txt"
	boundary, body = multipart(
		{
			"doctype": "LMS Assignment Submission",
			"docname": submission_name,
			"fieldname": "assignment_attachment",
			"folder": "Home",
			"is_private": "0",
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
	assert status == 200, f"Normal upload_file request failed: HTTP {status}"
	uploaded = message(json.loads(uploaded_body))
	file_url, file_name = uploaded.get("file_url"), uploaded.get("name")
	assert int(uploaded.get("is_private") or 0) == 1, "upload_file(is_private=0) created a public homework attachment"
	assert file_url and file_url.startswith("/private/files/"), "Homework upload did not use private storage"
	assert uploaded.get("owner") == student_email, "Uploaded File owner did not match the authenticated learner"
	assert (
		uploaded.get("attached_to_doctype") == "LMS Assignment Submission"
		and uploaded.get("attached_to_name") == submission_name
		and uploaded.get("attached_to_field") == "assignment_attachment"
	), "upload_file did not link the private File to the submission field"

	# Exercise the ordinary document API explicitly, then reopen the submission.
	status, saved = api(
		owner,
		"frappe.client.set_value",
		{
			"doctype": "LMS Assignment Submission",
			"name": submission_name,
			"fieldname": "assignment_attachment",
			"value": file_url,
		},
	)
	assert status == 200, f"Owner could not save the uploaded attachment reference: HTTP {status}"
	status, reopened = api(
		owner, "frappe.client.get", {"doctype": "LMS Assignment Submission", "name": submission_name}
	)
	assert status == 200 and message(reopened).get("assignment_attachment") == file_url, (
		"Owner could not reopen the submission with its attachment reference"
	)

	# Administrator is used only to enumerate synthetic duplicate-URL records.
	admin = login("Administrator", ADMIN_PASS)
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
	assert any(row.get("name") == file_name for row in duplicate_rows), (
		"Administrator File listing did not find the just-uploaded synthetic file"
	)

	clients = {
		"owner": (owner, student_email, True),
		"other student": (login("student2@over-u.example.com"), "student2@over-u.example.com", False),
		"assigned teacher": (login("teacher@over-u.example.com"), "teacher@over-u.example.com", True),
		"unrelated Course Creator": (
			login("over-u-unrelated-teacher@example.com"),
			"over-u-unrelated-teacher@example.com",
			False,
		),
	}
	guest = client()
	actors = [("Guest", guest, "Guest", False), *[(label, *entry) for label, entry in clients.items()]]
	public_path = "/files/" + file_url.rsplit("/", 1)[-1]
	results = {}

	for label, session, identity, allowed in actors:
		assert_identity(session, identity)
		plain_status, plain_body, _ = request(session, file_url)
		assert_identity(session, identity)
		fid_status, fid_body, _ = request(session, file_url + "?" + urlencode({"fid": file_name}))
		assert_identity(session, identity)
		handler_status, handler_body, _ = request(
			session,
			"/api/method/frappe.handler.download_file?"
			+ urlencode({"file_url": file_url, "fid": file_name}),
		)
		public_status, public_body, _ = request(session, public_path)

		file_status, file_payload = api(
			session, "frappe.client.get", {"doctype": "File", "name": file_name}
		)
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
	violations = []
	for label, method_results in results.items():
		allowed = label in ("owner", "assigned teacher")
		for method in ("plain_url", "plain_url_with_fid", "handler_download_file"):
			code, contains = method_results[method]
			if not ((code == 200 and contains) if allowed else (code != 200 and not contains)):
				violations.append(f"{label} {method}: HTTP {code}, sentinel={contains}")
		for method in ("file_get", "file_get_list"):
			code, visible = method_results[method]
			if visible != allowed:
				violations.append(f"{label} {method}: HTTP {code}, visible={visible}")
		for method in ("submission_get", "submission_get_list"):
			code, visible = method_results[method]
			if visible != allowed:
				violations.append(f"{label} {method}: HTTP {code}, visible={visible}")
		code, contains = method_results["public_files_url"]
		if code == 200 and contains:
			violations.append(f"{label} public_files_url exposed sentinel: HTTP {code}")

	print("Synthetic upload metadata:", json.dumps({key: uploaded.get(key) for key in FILE_FIELDS}, sort_keys=True))
	print("Same-URL File rows:", json.dumps(duplicate_rows, sort_keys=True))
	print("HTTP authorization matrix:", json.dumps(results, sort_keys=True))
	if len(duplicate_rows) != 1:
		violations.append(f"Ambiguous same-URL File count: {len(duplicate_rows)}")
	if violations:
		raise AssertionError("HTTP canary failures: " + " | ".join(violations))


if __name__ == "__main__":
	main()
