import json
import unittest
from unittest.mock import patch

from backend.services.ai_service import AIService


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class PodcastResourceTests(unittest.TestCase):
    def setUp(self):
        self.service = AIService()

    def test_direct_episode_url_detection(self):
        self.assertTrue(
            self.service._is_direct_podcast_episode_url(
                "https://podcasts.apple.com/us/podcast/show/id123?i=100012345"
            )
        )
        self.assertTrue(
            self.service._is_direct_podcast_episode_url(
                "https://open.spotify.com/episode/abc123"
            )
        )
        self.assertFalse(
            self.service._is_direct_podcast_episode_url(
                "https://podcasts.apple.com/search?term=machine+learning"
            )
        )

    @patch("backend.services.ai_service.urlopen")
    def test_apple_search_returns_direct_episode(self, mocked_urlopen):
        mocked_urlopen.return_value = _Response(
            {
                "results": [
                    {
                        "trackName": "Machine Learning in Education",
                        "collectionName": "Teaching Today",
                        "shortDescription": "How machine learning changes classrooms.",
                        "trackViewUrl": (
                            "https://podcasts.apple.com/us/podcast/teaching-today/"
                            "id123?i=100012345"
                        ),
                    }
                ]
            }
        )

        result = self.service._search_apple_podcast_episode(
            "machine learning", "AI in Education"
        )

        self.assertIsNotNone(result)
        self.assertIn("?i=100012345", result.url)
        self.assertEqual("podcast", result.resource_type)

    @patch.object(AIService, "_search_resource_variants", return_value=None)
    @patch.object(AIService, "_search_apple_podcast_episode", return_value=None)
    @patch.object(AIService, "_search_listennotes", return_value=None)
    def test_no_search_page_fallback(self, *_mocks):
        result = self.service._search_podcast_resource(
            "Highly Specific Document", "nonexistent specialist topic"
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
