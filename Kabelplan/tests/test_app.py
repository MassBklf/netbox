import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('requests.get')
    def test_filter_options(self, mock_get):
        # Mock NetBox responses
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [], "next": None}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = self.app.get('/api/filter-options')
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn('sites', data)
        self.assertIn('locations', data)
        self.assertIn('racks', data)

    @patch('requests.get')
    def test_graph_data(self, mock_get):
        # Mock responses
        def side_effect(url, headers, params=None):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if "dcim/devices" in url:
                resp.json.return_value = {
                    "results": [
                        {
                            "id": 1,
                            "name": "Dev1",
                            "device_role": {"name": "Switch"},
                            "device_type": {"model": "ModelX"},
                            "location": {"name": "Loc1"}
                        }
                    ],
                    "next": None
                }
            elif "dcim/cables" in url:
                resp.json.return_value = {
                    "results": [
                        {
                            "id": 100,
                            "label": "Cable1",
                            "termination_a": {"device": {"id": 1, "name": "Dev1"}, "name": "Eth0"},
                            "termination_b": {"device": {"id": 2, "name": "Dev2"}, "name": "Eth0"}
                        }
                    ],
                    "next": None
                }
            return resp

        mock_get.side_effect = side_effect

        response = self.app.get('/api/graph-data?site=test-site')
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn('nodes', data)
        self.assertIn('edges', data)

        # Verify device 1 (fetched) is in nodes
        self.assertTrue(any(n['id'] == 1 for n in data['nodes']))
        # Verify device 2 (external but connected) is in nodes
        self.assertTrue(any(n['id'] == 2 for n in data['nodes']))
        # Verify edge
        self.assertTrue(any('Cable1' in e['label'] for e in data['edges']))
        self.assertTrue(any('Eth0 <-> Eth0' in e['label'] for e in data['edges']))

if __name__ == '__main__':
    unittest.main()
