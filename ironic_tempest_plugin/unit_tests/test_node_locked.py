#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import itertools
import unittest
from unittest import mock

from tempest.lib import exceptions as lib_exc

from ironic_tempest_plugin.common import waiters
from ironic_tempest_plugin.services.baremetal import base

NODE = '0212ce84-673c-4636-8b99-6284d2380d39'
LOCKED = ('{"error_message": "Node %s is locked by host host1, please '
          'retry after the current operation is completed."}' % NODE)


class FakeClient(object):
    def __init__(self, results):
        self.calls = 0
        self._results = list(results)

    @base.retry_on_node_locked
    def set_node_provision_state(self, node_uuid, state):
        self.calls += 1
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@mock.patch('tenacity.nap.time.sleep', autospec=True)
class TestRetryOnNodeLocked(unittest.TestCase):

    def test_retries_until_unlocked(self, mock_sleep):
        client = FakeClient([lib_exc.Conflict(LOCKED),
                             lib_exc.Conflict(LOCKED),
                             'ok'])
        self.assertEqual(
            'ok', client.set_node_provision_state(NODE, 'provide'))
        self.assertEqual(3, client.calls)
        self.assertEqual([mock.call(2), mock.call(4)],
                         mock_sleep.call_args_list)

    def test_gives_up_after_three_retries(self, mock_sleep):
        client = FakeClient([lib_exc.Conflict(LOCKED)] * 4)
        self.assertRaises(lib_exc.Conflict,
                          client.set_node_provision_state, NODE, 'provide')
        self.assertEqual(4, client.calls)
        self.assertEqual(3, mock_sleep.call_count)

    def test_other_conflict_not_retried(self, mock_sleep):
        client = FakeClient([lib_exc.Conflict(
            '{"error_message": "Cannot provide a node in state active"}')])
        self.assertRaises(lib_exc.Conflict,
                          client.set_node_provision_state, NODE, 'provide')
        self.assertEqual(1, client.calls)
        mock_sleep.assert_not_called()

    def test_other_error_not_retried(self, mock_sleep):
        client = FakeClient([lib_exc.BadRequest(LOCKED)])
        self.assertRaises(lib_exc.BadRequest,
                          client.set_node_provision_state, NODE, 'provide')
        self.assertEqual(1, client.calls)


@mock.patch('time.sleep', autospec=True)
class TestWaitForUnlock(unittest.TestCase):

    @staticmethod
    def _client(*nodes):
        client = mock.Mock(build_timeout=60, build_interval=1)
        client.show_node.side_effect = [(None, n) for n in nodes]
        return client

    def test_waits_for_reservation_to_clear(self, mock_sleep):
        client = self._client(
            {'provision_state': 'manageable', 'reservation': 'host1'},
            {'provision_state': 'manageable', 'reservation': 'host1'},
            {'provision_state': 'manageable', 'reservation': None})
        waiters.wait_for_bm_node_status(
            client, NODE, 'provision_state', 'manageable',
            wait_for_unlock=True)
        self.assertEqual(3, client.show_node.call_count)

    def test_ignores_reservation_by_default(self, mock_sleep):
        client = self._client(
            {'provision_state': 'manageable', 'reservation': 'host1'})
        waiters.wait_for_bm_node_status(
            client, NODE, 'provision_state', 'manageable')
        self.assertEqual(1, client.show_node.call_count)

    @mock.patch('tempest.lib.common.utils.test_utils.time', autospec=True)
    def test_timeout_message_has_last_seen(self, mock_time, mock_sleep):
        mock_time.time.side_effect = itertools.chain(
            [0, 0.1], itertools.repeat(2))
        locked = {'provision_state': 'manageable', 'reservation': 'host1'}
        client = self._client(locked, locked, locked)
        with self.assertRaises(lib_exc.TimeoutException) as ctx:
            waiters.wait_for_bm_node_status(
                client, NODE, 'provision_state', 'manageable', timeout=1,
                wait_for_unlock=True)
        self.assertIn('and be unlocked', str(ctx.exception))
        self.assertIn('provision_state=manageable', str(ctx.exception))
        self.assertIn('reservation=host1', str(ctx.exception))
