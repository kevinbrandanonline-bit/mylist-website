import json
import unittest

from app import app


class BiblerAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_home_page_renders_bibler_shell(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Bibler', response.data)
        self.assertIn(b'Dashboard', response.data)
        self.assertIn(b'Prayer Journal', response.data)

    def test_prayers_api_returns_json(self):
        response = self.client.get('/api/prayers')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

    def test_prayer_can_be_created(self):
        response = self.client.post('/api/prayers', json={
            'title': 'Family peace',
            'body': 'Pray for calm and unity.'
        })
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload['title'], 'Family peace')

    def test_bible_search_uses_extracted_verses(self):
        response = self.client.get('/api/search?query=beginning')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload)
        self.assertIn('beginning', payload[0]['text'].lower())

    def test_books_page_lists_bible_books(self):
        response = self.client.get('/books')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Genesis', response.data)
        self.assertIn(b'Revelation', response.data)

    def test_book_detail_page_shows_book_summary(self):
        response = self.client.get('/book/Genesis')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Genesis', response.data)
        self.assertIn(b'Creation', response.data)


if __name__ == '__main__':
    unittest.main()
