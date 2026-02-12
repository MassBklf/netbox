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
                            "termination_a": {"id": 10, "device": {"id": 1, "name": "Dev1"}, "name": "Eth0"},
                            "termination_b": {"id": 20, "device": {"id": 2, "name": "Dev2"}, "name": "Eth0"}
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

        # Verify nodes exist: 2 Devices + 2 Interfaces = 4 nodes
        node_ids = [n['id'] for n in data['nodes']]
        self.assertIn(1, node_ids)      # Dev1
        self.assertIn(2, node_ids)      # Dev2
        self.assertIn('if_10', node_ids) # Eth0 of Dev1
        self.assertIn('if_20', node_ids) # Eth0 of Dev2

        # Verify edges exist:
        # Dev1 -> if_10
        # Dev2 -> if_20
        # if_10 -> if_20 (Cable)
        edge_pairs = [(e['from'], e['to']) for e in data['edges']]
        self.assertIn((1, 'if_10'), edge_pairs)
        self.assertIn((2, 'if_20'), edge_pairs)
        self.assertIn(('if_10', 'if_20'), edge_pairs)

        # Verify Cable Label is on the interface-interface edge
        cable_edge = next(e for e in data['edges'] if e['from'] == 'if_10' and e['to'] == 'if_20')
        self.assertIn('Cable1', cable_edge['label'])

if __name__ == '__main__':
    unittest.main()
