import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Create a mock for pynetbox before importing app
mock_pynetbox = MagicMock()
sys.modules['pynetbox'] = mock_pynetbox

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import app module
import app as app_module

class TestKabelplan(unittest.TestCase):
    def setUp(self):
        self.app = app_module.app
        self.client = self.app.test_client()
        self.client.testing = True

        # Access the 'nb' variable in the module
        self.mock_nb = app_module.nb

    def test_get_graph_data(self):
        # Mock Devices
        mock_device1 = MagicMock()
        mock_device1.id = 1
        mock_device1.name = "Device1"
        mock_device1.device_type.model = "ModelX"
        mock_device1.device_role.name = "Router"

        mock_device2 = MagicMock()
        mock_device2.id = 2
        mock_device2.name = "Device2"
        mock_device2.device_type.model = "ModelY"
        mock_device2.device_role.name = "Switch"

        # When calling .filter(), return the list
        self.mock_nb.dcim.devices.filter.return_value = [mock_device1, mock_device2]

        # Mock Interfaces
        # We need to handle the fact that interfaces are fetched in a loop or batch
        # app.py: list(nb.dcim.interfaces.filter(device_id=chunk))

        i1 = MagicMock()
        i1.id = 101
        i1.name = "eth0"
        i1.device.id = 1

        i2 = MagicMock()
        i2.id = 102
        i2.name = "eth0"
        i2.device.id = 2

        self.mock_nb.dcim.interfaces.filter.return_value = [i1, i2]

        # Mock Cables
        mock_cable = MagicMock()
        mock_cable.id = 500
        mock_cable.label = "Cable1"
        mock_cable.color = "blue"

        # Terminations
        term_a = MagicMock()
        term_a.device.id = 1
        term_a.id = 101

        term_b = MagicMock()
        term_b.device.id = 2
        term_b.id = 102

        # In app.py we access cable.a_terminations[0]
        # So we need to ensure a_terminations is a list
        mock_cable.a_terminations = [term_a]
        mock_cable.b_terminations = [term_b]

        self.mock_nb.dcim.cables.filter.return_value = [mock_cable]

        # Call API
        response = self.client.get('/api/graph-data?site=test-site')

        # Check for errors
        if response.status_code != 200:
            print(response.get_json())

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        # Verify Nodes
        self.assertEqual(len(data['nodes']), 2)

        # Check Device1
        node1 = next((n for n in data['nodes'] if n['id'] == '1'), None)
        self.assertIsNotNone(node1)
        self.assertEqual(node1['name'], "Device1")

        # Check Ports on Device1
        self.assertTrue(len(node1['ports']) >= 1)
        self.assertEqual(node1['ports'][0]['id'], '101')

        # Verify Links
        self.assertEqual(len(data['links']), 1)
        link = data['links'][0]
        self.assertEqual(link['source']['id'], '1')
        self.assertEqual(link['source']['port'], '101')
        self.assertEqual(link['target']['id'], '2')
        self.assertEqual(link['target']['port'], '102')

if __name__ == '__main__':
    unittest.main()
