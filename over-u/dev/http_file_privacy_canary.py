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
UPLOAD_PROBE = json.loads(os.environ["OVER_U_UPLOAD_PROBE"])


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


def login(email):
	client_ = client()
	status, payload = api(client_, "login", {"usr": email, "pwd": PASS})
	assert status == 200, f"Synthetic login failed for {email}: HTTP {status}: {payload}"
	status, session = api(client_, "frappe.auth.get_logged_user", {})
	assert (
		status == 200 and session.get("message") == email
	), f"Login did not establish the expected session for {email}: HTTP {status}: {session}"
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


def has_payload(result):
	return SENTINEL.decode() in json.dumps(result, ensure_ascii=False)


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
	assert status == 200, f"Normal student submission insert failed: HTTP {status}: {inserted}"
	submission_name = inserted.get("message", {}).get("name")
	assert submission_name, f"Normal student insert returned no submission name: {inserted}"

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
	assert status == 200, f"Normal upload_file request failed: HTTP {status}: {uploaded_body[:300]!r}"
	uploaded = json.loads(uploaded_body).get("message", {})
	file_url = uploaded.get("file_url")
	file_name = uploaded.get("name")
	assert (
		int(uploaded.get("is_private") or 0) == 1
	), f"upload_file(is_private=0) did not force File.is_private=1: {uploaded}"
	assert file_url and file_url.startswith(
		"/private/files/"
	), f"Homework upload was not stored under /private/files/: {file_url!r}"

	assert (
		uploaded.get("attached_to_doctype") == "LMS Assignment Submission"
		and uploaded.get("attached_to_name") == submission_name
		and uploaded.get("attached_to_field") == "assignment_attachment"
	), f"upload_file did not link the private File to the submission field: {uploaded}"

	clients = {
		"owner": owner,
		"other student": login("student2@over-u.example.com"),
		"assigned teacher": login("teacher@over-u.example.com"),
		"unrelated Course Creator": login("over-u-unrelated-teacher@example.com"),
	}
	private_path = file_url
	public_path = "/files/" + file_url.rsplit("/", 1)[-1]
	file_get_method = "frappe.handler.download_file"
	file_api_visibility = {}

	for label, session in (("Guest", client()), *clients.items()):
		status, body, _headers = request(session, private_path)
		allowed = label in ("owner", "assigned teacher")
		assert (
			(status == 200 and SENTINEL in body) if allowed else (status != 200 and SENTINEL not in body)
		), f"Direct private URL policy mismatch for {label}: HTTP {status}"

		status, body, _headers = request(session, public_path)
		assert status != 200 or SENTINEL not in body, f"{label} fetched the homework through /files/"

		status, body, _headers = request(
			session, "/api/method/frappe.handler.download_file?" + urlencode({"file_url": file_url})
		)
		allowed = label in ("owner", "assigned teacher")
		assert (
			(status == 200 and SENTINEL in body) if allowed else (status != 200 and SENTINEL not in body)
		), f"{file_get_method} policy mismatch for {label}: HTTP {status}"

		status, file_doc = api(session, "frappe.client.get", {"doctype": "File", "name": file_name})
		file_doc_json = json.dumps(file_doc)
		file_doc_message = file_doc.get("message")
		if not isinstance(file_doc_message, dict):
			file_doc_message = {}
		file_doc_visible = status == 200 and file_doc_message.get("file_url") == file_url
		assert file_doc_message.get("file_url") in (None, file_url), (
			f"frappe.client.get File returned a different URL for {label}: HTTP {status}"
		)
		if not allowed:
			assert (
				not file_doc_visible
				and file_name not in file_doc_json
				and file_url not in file_doc_json
				and not has_payload(file_doc)
			), f"frappe.client.get exposed the private File to {label}: HTTP {status}"

		status, file_rows = api(
			session,
			"frappe.client.get_list",
			{
				"doctype": "File",
				"filters": {"name": file_name},
				"fields": ["name", "file_url"],
				"limit_page_length": 10,
			},
		)
		rows = file_rows.get("message", [])
		if not isinstance(rows, list):
			rows = []
		visible = any(row.get("name") == file_name for row in rows)
		assert not visible or allowed, (
			f"frappe.client.get_list exposed the private File to {label}: HTTP {status}"
		)
		if visible:
			assert all(row.get("file_url") == file_url for row in rows)
		if not allowed:
			file_rows_json = json.dumps(file_rows)
			assert (
				file_name not in file_rows_json
				and file_url not in file_rows_json
				and not has_payload(file_rows)
			), f"frappe.client.get_list leaked private File metadata to {label}: HTTP {status}"
		file_api_visibility[label] = {"get": file_doc_visible, "get_list": visible}

		status, submission = api(
			session, "frappe.client.get", {"doctype": "LMS Assignment Submission", "name": submission_name}
		)
		assert (
			(status == 200 and submission.get("message", {}).get("assignment_attachment") == file_url)
			if allowed
			else (status != 200 and not has_payload(submission) and file_url not in json.dumps(submission))
		), f"frappe.client.get submission policy mismatch for {label}: HTTP {status}"

		status, submission_rows = api(
			session,
			"frappe.client.get_list",
			{
				"doctype": "LMS Assignment Submission",
				"filters": {"name": submission_name},
				"fields": ["name"],
				"limit_page_length": 10,
			},
		)
		visible = any(row.get("name") == submission_name for row in submission_rows.get("message", []))
		assert (
			visible == allowed
		), f"frappe.client.get_list submission policy mismatch for {label}: HTTP {status}, visible={visible}"

	print(
		"frappe.client.insert created a submission as the student; "
		"upload_file(is_private=0) stored its attachment privately."
	)
	print(
		"Guest, another student, and unrelated Course Creator were denied; owner and assigned teacher were allowed."
	)
	print("Direct URL, handler download, frappe.client.get/get_list, and /files/ path checks passed.")
	print("File metadata API visibility:", json.dumps(file_api_visibility, sort_keys=True))


if __name__ == "__main__":
	main()
