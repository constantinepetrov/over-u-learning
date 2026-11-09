from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from over_u import video_api

YANDEX = "https://disk.yandex.ru/i/XZW01pZKSkJmFA"
RUTUBE = "https://rutube.ru/video/0123456789abcdef0123456789abcdef/"
YOUTUBE = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


class TestVideoLinks(IntegrationTestCase):
	def test_supported_links_become_safe_players(self):
		self.assertEqual(video_api.parse(YANDEX)["kind"], "yandex")
		rutube = video_api.parse(RUTUBE)
		self.assertEqual(rutube["src"], "https://rutube.ru/play/embed/0123456789abcdef0123456789abcdef")
		youtube = video_api.parse(YOUTUBE)
		self.assertEqual(youtube["src"], "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ")
		self.assertEqual(video_api.parse("https://youtu.be/dQw4w9WgXcQ")["kind"], "embed")
		vk = video_api.parse("https://vk.com/video-12345_67890")
		self.assertEqual(vk["src"], "https://vk.com/video_ext.php?oid=-12345&id=67890&hd=2")

	def test_other_links_are_refused(self):
		for bad in (
			"",
			"javascript:alert(1)",
			"http://disk.yandex.ru/i/XZW01pZKSkJmFA",
			"https://evil.example/i/XZW01pZKSkJmFA",
			"https://disk.yandex.ru.evil.example/i/XZW01pZKSkJmFA",
			"https://rutube.ru/video/not-an-id/",
			"https://www.youtube.com/watch?v=short",
			'https://vk.com/video_ext.php?oid=1&id=2"onload="x',
			"https://disk.yandex.ru/i/" + "a" * 600,
		):
			self.assertIsNone(video_api.parse(bad), bad)
		with self.assertRaises(frappe.ValidationError):
			video_api.clean("https://example.com/video.mp4")
		self.assertEqual(video_api.clean("  "), "")

	def test_yandex_address_is_cached_and_only_from_yandex(self):
		link = "https://disk.yandex.ru/i/CacheTest123"
		for key in ("", "_busy"):
			frappe.cache.delete_value(
				"over_u_yandex_" + __import__("hashlib").sha256(link.encode()).hexdigest() + key
			)
		good = "https://downloader.disk.yandex.ru/disk/abc/file.mp4"

		class Reply:
			status_code = 200

			def __init__(self, href):
				self.href = href

			def json(self):
				return {"href": self.href}

		with patch("over_u.video_api.requests.get", return_value=Reply(good)) as get:
			self.assertEqual(video_api._direct_address(link), good)
			self.assertEqual(video_api._direct_address(link), good)
			self.assertEqual(get.call_count, 1)
		other = "https://disk.yandex.ru/i/OtherLink456"
		with patch("over_u.video_api.requests.get", return_value=Reply("https://evil.example/x.mp4")):
			self.assertEqual(video_api._direct_address(other), "")
