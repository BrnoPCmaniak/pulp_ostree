from unittest import TestCase

from mock import Mock, patch

from pulp_ostree.common.constants import OSTREE_TYPE_ID
from pulp_ostree.extensions.admin.unit import format_unit, CopyCommand, RemoveCommand, SearchCommand


class TestFunctions(TestCase):

    def test_format(self):
        unit = dict(remote_id='test-id', digest='test-digest')
        formatted = format_unit(unit)
        self.assertEqual(formatted, 'remote_id: test-id digest: test-digest')


class TestCopyCommand(TestCase):

    def test_command(self):
        context = Mock()
        context.config = {
            'output': {'poll_frequency_in_seconds': 1}
        }
        command = CopyCommand(context)
        fn = command.get_formatter_for_type(OSTREE_TYPE_ID)
        self.assertEqual(fn, format_unit)


class TestRemoveCommand(TestCase):

    def test_command(self):
        context = Mock()
        context.config = {
            'output': {'poll_frequency_in_seconds': 1}
        }
        command = RemoveCommand(context)
        fn = command.get_formatter_for_type(OSTREE_TYPE_ID)
        self.assertEqual(fn, format_unit)


class TestSearchCommand(TestCase):

    def test_filtering(self):
        units = [
            {
                'id': 0,
                'created': 1,
                'updated': 2,
                'metadata': {
                    'remote_id': 3,
                    'digest': 4,
                    'refs': 5
                }
            },
            {
                'id': 10,
                'created': 11,
                'updated': 12,
                'metadata': {
                    'remote_id': 13,
                    'digest': 14,
                    'refs': 15
                }
            }
        ]

        # test
        documents = SearchCommand.filter(units)

        # validation
        self.assertEqual(
            documents,
            [
                {
                    'id': 0,
                    'created': 1,
                    'updated': 2,
                    'remote_id': 3,
                    'digest': 4,
                    'refs': 5
                },
                {
                    'id': 10,
                    'created': 11,
                    'updated': 12,
                    'remote_id': 13,
                    'digest': 14,
                    'refs': 15
                }
            ])

    @patch('pulp_ostree.extensions.admin.unit.SearchCommand.filter')
    def test_run(self, fake_filter):
        repo_id = 'test-repo'
        units = Mock()
        context = Mock()
        context.server.repo_unit.search.return_value = Mock(response_body=units)
        keywords = {'repo-id': repo_id, 'kw-1': 'v-1'}
        context.config = {
            'output': {'poll_frequency_in_seconds': 1}
        }

        # test
        command = SearchCommand(context)
        command.run(**keywords)

        # validation
        keywords.pop('repo-id')
        context.server.repo_unit.search.assert_called_once_with(repo_id, **keywords)
        context.prompt.render_title.assert_called_once_with(SearchCommand.TITLE)
        context.prompt.render_document_list.assert_called_once_with(
            fake_filter.return_value, order=SearchCommand.ORDER)
