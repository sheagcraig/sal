"""Beginning of the test setup for non_ui_views"""


import base64
import bz2
import datetime
import plistlib
import pytz
from unittest.mock import patch

from django.conf import settings
from django.http.response import Http404
from django.test import TestCase, Client

from server.models import MachineGroup, Machine
from server import non_ui_views


class CheckinDataTest(TestCase):
    """Functional tests for client checkins."""

    fixtures = ['machine_group_fixture.json', 'business_unit_fixture.json', 'machine_fixture.json']

    def setUp(self):
        settings.BASIC_AUTH = False
        self.client = Client()
        self.content_type = 'content-type application/x-www-form-urlencoded'

    def test_checkin_requires_key_auth(self):
        """Ensure that key auth is enforced."""
        settings.BASIC_AUTH = True
        response = self.client.post('/checkin/', data={})
        self.assertEqual(response.status_code, 401)

    def test_checkin_data_empty(self):
        """Ensure that checkins with missing data get a 404 response."""
        response = self.client.post('/checkin/', data={}, content_type=self.content_type)
        self.assertEqual(response.status_code, 404)

    def test_checkin_incorrect_content_type(self):
        """Ensure checkin only accepts form encoded data."""
        response = self.client.post(
            '/checkin/', data={'serial': 'C0DEADBEEF'}, content_type='text/xml')
        # Should return 404 when looking up the machine's serial
        # number, which should be absent when sent with the wrong
        # content_type.
        self.assertEqual(response.status_code, 404)

    def test_deployed_on_checkin(self):
        """Test that a machine's deployed bool gets toggled."""
        machine = Machine.objects.get(serial='C0DEADBEEF')
        machine.deployed = False
        machine.save()
        settings.DEPLOYED_ON_CHECKIN = True
        self.client.post(
            '/checkin/', data={'serial': machine.serial, 'key': machine.machine_group.key})
        machine.refresh_from_db()
        self.assertTrue(machine.deployed)

    def test_not_deployed_on_checkin(self):
        """Test that a machine's deployed bool is not updated on checkin."""
        machine = Machine.objects.get(serial='C0DEADBEEF')
        machine.deployed = False
        settings.DEPLOYED_ON_CHECKIN = False
        machine.save()
        self.client.post(
            '/checkin/', data={'serial': machine.serial, 'key': machine.machine_group.key})
        machine.refresh_from_db()
        self.assertFalse(machine.deployed)

    def test_broken_client_checkin(self):
        """Test that a machine's deployed bool is not updated on checkin."""
        machine = Machine.objects.get(serial='C0DEADBEEF')
        data = {
            'serial': machine.serial, 'key': machine.machine_group.key, 'broken_client': 'True'}
        self.client.post('/checkin/', data=data)
        machine.refresh_from_db()
        self.assertTrue(machine.broken_client)

    def test_bad_report_data_type(self):
        """Test checkin can complete with bare minimum data and bad report."""
        machine = Machine.objects.get(serial='C0DEADBEEF')
        data = {
            'serial': machine.serial,
            'key': machine.machine_group.key,
            'base64report': (b'SSBhbSBhIHNlcnZhbnQgb2YgdGhlIFNlY3JldCBGaXJlLCB3aWVsZGVyIG9mIHRoZSBm'
                             b'bGFtZSBvZiBBbm9yLiBZb3UgY2Fubm90IHBhc3MhIFRoZSBkYXJrIGZpcmUgd2lsbCBu'
                             b'b3QgYXZhaWwgeW91LCBmbGFtZSBvZiBVZMO7bi4=')}
        response = self.client.post('/checkin/', data=data)
        self.assertEqual(response.status_code, 200)

    def test_no_report_completes(self):
        """Test checkin can complete with only the essential data."""
        machine = Machine.objects.get(serial='C0DEADBEEF')
        data = {'serial': machine.serial, 'key': machine.machine_group.key}
        response = self.client.post('/checkin/', data=data)
        self.assertEqual(response.status_code, 200)

    @patch('server.models.Machine.save')
    @patch('utils.text_utils.submission_plist_loads')
    def test_incorrect_data_type_stops_early(self, mock_plist_loads, mock_save):
        """Test that invalid data types in the report bail with a 500."""
        machine = Machine.objects.get(serial='C0DEADBEEF')
        mock_plist_loads.return_value = {'Puppet': {'events': {'failure': 'nyancat'}}}

        def raise_value_error():
            raise ValueError
        # Mock out the save failing when trying to commit a str to an
        # IntegerField. There's a way to do this with
        # django.db.transaction.atomic as a context manager, but that
        # is only a problem when testing.
        mock_save.side_effect = raise_value_error

        data = {'serial': machine.serial, 'key': machine.machine_group.key}
        response = self.client.post('/checkin/', data=data)
        self.assertEqual(response.status_code, 500)


class CheckinHelperTest(TestCase):
    """Tests for helper functions that support the checkin view."""

    fixtures = ['machine_group_fixture.json', 'business_unit_fixture.json', 'machine_fixture.json']

    def setUp(self):
        self.report = {'test': 'I heard you were dead'}

    def test_checkin_memory_value_conversion(self):
        """Ensure conversion of memory to memory_kb is correct"""

        # hash of string description to number of KB
        memconv = {'4 GB': 4194304,
                   '8 GB': 8388608,
                   '1 TB': 1073741824}

        # pass each value and check proper value returned
        test_machine = Machine(serial='testtesttest123')
        for key in memconv:
            test_machine.memory = key
            self.assertEqual(non_ui_views.process_memory(test_machine), memconv[key])

    def test_vmware_serial(self):
        """Ensure serial translation for crazy VMWare serials works."""
        machine = non_ui_views.process_checkin_serial('+/c0deadbEEF')
        self.assertEqual(machine.serial, 'C0DEADBEEF')

    def test_machine_from_valid_serial(self):
        """Ensure we can get an existing Machine object."""
        machine = non_ui_views.process_checkin_serial('C0DEADBEEF')
        self.assertEqual(machine.pk, 1)

    def test_add_new_machine(self):
        """Ensure we can add a new machine with ADD_NEW_MACHINES=True"""
        machine = non_ui_views.process_checkin_serial('NotInDB')
        self.assertEqual(machine.pk, None)

    def test_no_add_new_machine(self):
        """Ensure 404 is raised when no ADD_NEW_MACHINES."""
        settings.ADD_NEW_MACHINES = False
        self.assertRaises(Http404, non_ui_views.process_checkin_serial, 'NotInDB')

    def test_get_checkin_machine_group(self):
        """Test basic function."""
        group = MachineGroup.objects.get(pk=1)
        self.assertEqual(non_ui_views.get_checkin_machine_group(group.key), group)

    def test_get_checkin_machine_group_bad_key(self):
        """Test basic function."""
        self.assertRaises(Http404, non_ui_views.get_checkin_machine_group, 'NotInDB')

    def test_get_checkin_machine_group_default(self):
        """Test basic function."""
        group = MachineGroup.objects.get(pk=1)
        settings.DEFAULT_MACHINE_GROUP_KEY = group.key
        self.assertEqual(non_ui_views.get_checkin_machine_group(None), group)

    def test_get_console_user(self):
        """Test that user can be safely set from helper function."""
        user = 'Snake Plisskin'
        report = {'ConsoleUser': user}
        self.assertTrue(non_ui_views.get_console_user(report), user)
        report = {'username': user}
        self.assertTrue(non_ui_views.get_console_user(report), user)
        self.assertEqual(non_ui_views.get_console_user({}), None)

    def test_get_report_bytes_b64(self):
        """Ensure base64 encoded reports can be retrieved."""
        report = base64.b64encode(plistlib.dumps(self.report))
        data = {'base64report': report}
        self.assertEqual(non_ui_views.get_report_bytes(data), plistlib.dumps(self.report))

    def test_get_report_bytes_bz2(self):
        """Ensure bz2 compressed reports can be retrieved."""
        report = bz2.compress(plistlib.dumps(self.report))
        data = {'bz2report': report}
        self.assertEqual(non_ui_views.get_report_bytes(data), plistlib.dumps(self.report))

    def test_get_report_bytes_bz2b64(self):
        """Ensure base64 encoded bz2 compressed reports can be retrieved."""
        report = base64.b64encode(bz2.compress(plistlib.dumps(self.report)))
        data = {'base64bz2report': report}
        self.assertEqual(non_ui_views.get_report_bytes(data), plistlib.dumps(self.report))

    def test_process_puppet_no_data(self):
        """Ensure a non-puppet client passes this func."""
        report = {}
        machine = non_ui_views.process_puppet_data(report, Machine.objects.get(pk=1))
        checked_attrs = (machine.puppet_version, machine.puppet_errors)
        checked = all(not attr for attr in checked_attrs)
        self.assertTrue(checked)
        # We're simulating checking a puppetless client; but the
        # fixture has a last_puppet_run, which we should retain even if
        # puppet has been removed.
        self.assertTrue(machine.last_puppet_run)

    def test_process_puppet(self):
        """Ensure a non-puppet client passes this func."""
        report = {
            'Puppet_Version': '1.0.0',
            'Puppet': {'time': {'last_run': 1000},
                       'events': {'failure': 99}}}
        machine = non_ui_views.process_puppet_data(report, Machine.objects.get(pk=1))
        self.assertEqual(machine.puppet_version, report['Puppet_Version'])
        self.assertEqual(
            machine.last_puppet_run,
            datetime.datetime.fromtimestamp(report['Puppet']['time']['last_run'], pytz.UTC))

    def test_process_puppet_bad_data(self):
        """Ensure a non-puppet client passes this func."""
        report = {
            'Puppet_Version': False,
            'Puppet': {'time': {'last_run': 'last monday'},
                       'events': {'failure': 'never ever'}}}
        machine = Machine.objects.get(pk=1)
        last_run = machine.last_puppet_run
        machine = non_ui_views.process_puppet_data(report, machine)
        self.assertEqual(machine.puppet_version, False)
        self.assertEqual(machine.puppet_errors, 0)
        self.assertEqual(machine.last_puppet_run, last_run)
