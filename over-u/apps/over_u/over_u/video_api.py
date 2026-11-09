"""Lesson video by link: Yandex Disk, RuTube, VK Video and YouTube.

The video is never copied to this server. A link is stored on the lesson, and the school shows
either an embedded player (RuTube, VK Video, YouTube) or a plain player fed straight from Yandex
Disk. For Yandex Disk the school asks the public API for a short-lived direct address and sends
the browser there, so the stream goes from Yandex to the learner. The address is kept for a few
minutes to stay under the Yandex request limit when a whole group opens the lesson.
Only the four providers below are accepted; the embed address is always built from validated ids.
"""

import hashlib
import re
from urllib.parse import quote, urlparse

import frappe
import requests
from frappe import _

from over_u.student_api import _open_lesson

FIELD = "over_u_video_url"
MAX_URL = 500
YANDEX_API = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
YANDEX_LINK = re.compile(r"https://(?:disk\.yandex\.(?:ru|com|kz|by|ua)|yadi\.sk)/[id]/[A-Za-z0-9_-]{6,64}/?")
RUTUBE_LINK = re.compile(r"https://rutube\.ru/(?:video|play/embed)/([0-9a-f]{32})/?(?:\?[^\s#]*)?")
YOUTUBE_LINK = re.compile(
	r"https://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?(?:[^\s#]*&)?v=|embed/|shorts/)|youtu\.be/)"
	r"([A-Za-z0-9_-]{11})(?:[?&#/][^\s]*)?"
)
VK_LINK = re.compile(r"https://(?:vk\.com|vkvideo\.ru)/video(-?\d{1,12})_(\d{1,12})(?:\?[^\s#]*)?")
VK_EMBED = re.compile(r"https://vk\.com/video_ext\.php\?[A-Za-z0-9_=&%.-]+")
CACHE_SECONDS = 600
BUSY_SECONDS = 30


def parse(url):
	"""Return {"kind", "link", "src"} for a supported link, otherwise None."""
	if not isinstance(url, str):
		return None
	url = url.strip()
	if not url or len(url) > MAX_URL:
		return None
	if YANDEX_LINK.fullmatch(url):
		return {"kind": "yandex", "link": url, "src": ""}
	match = RUTUBE_LINK.fullmatch(url)
	if match:
		return {"kind": "embed", "link": url, "src": f"https://rutube.ru/play/embed/{match.group(1)}"}
	match = YOUTUBE_LINK.fullmatch(url)
	if match:
		return {
			"kind": "embed",
			"link": url,
			"src": f"https://www.youtube-nocookie.com/embed/{match.group(1)}",
		}
	match = VK_LINK.fullmatch(url)
	if match:
		query = re.search(r"[?&]hash=([0-9a-f]{8,32})", url)
		src = f"https://vk.com/video_ext.php?oid={match.group(1)}&id={match.group(2)}&hd=2"
		if query:
			src += f"&hash={query.group(1)}"
		return {"kind": "embed", "link": url, "src": src}
	if VK_EMBED.fullmatch(url):
		return {"kind": "embed", "link": url, "src": url}
	return None


def clean(url):
	"""Validated link for saving, empty string to clear it. Raises for an unsupported link."""
	url = (url or "").strip() if isinstance(url, str) else ""
	if not url:
		return ""
	if not parse(url):
		frappe.throw(_("Use a link to a video on Yandex Disk, RuTube, VK Video or YouTube."))
	return url


def lesson_block(course, number, lesson):
	"""The block the school shows for the lesson's video link, or None."""
	info = parse(frappe.db.get_value("Course Lesson", lesson, FIELD))
	if not info:
		return None
	if info["kind"] == "embed":
		return {"type": "embed", "src": info["src"], "link": info["link"]}
	stream = (
		"/api/method/over_u.video_api.stream?course="
		+ quote(course, safe="")
		+ "&number="
		+ quote(number, safe="")
	)
	return {"type": "video", "url": stream, "link": info["link"]}


def _direct_address(link):
	key = "over_u_yandex_" + hashlib.sha256(link.encode()).hexdigest()
	cache = frappe.cache
	if cache.get_value(key + "_busy"):
		return ""
	address = cache.get_value(key)
	if address:
		return address
	try:
		response = requests.get(YANDEX_API, params={"public_key": link}, timeout=8)
		address = response.json().get("href") if response.status_code == 200 else ""
	except (requests.RequestException, ValueError):
		address = ""
	host = urlparse(address or "").hostname or ""
	if not address or not address.startswith("https://") or not host.endswith((".yandex.ru", ".yandex.net")):
		cache.set_value(key + "_busy", 1, expires_in_sec=BUSY_SECONDS)
		return ""
	cache.set_value(key, address, expires_in_sec=CACHE_SECONDS)
	return address


@frappe.whitelist()
def stream(course: str, number: str):
	"""Send an enrolled learner (or the course's teacher) to the live Yandex Disk address."""
	lesson = _open_lesson(course, number)
	info = parse(frappe.db.get_value("Course Lesson", lesson.get("name"), FIELD))
	if not info or info["kind"] != "yandex":
		frappe.throw(_("Lesson not found."), frappe.DoesNotExistError)
	address = _direct_address(info["link"])
	if not address:
		frappe.throw(
			_("The video is temporarily unavailable. Try again in a minute."), frappe.ValidationError
		)
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = address
