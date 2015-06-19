import os
import errno

from unittest import TestCase

from mock import patch, Mock, PropertyMock, ANY

from pulp.common.plugins import importer_constants
from pulp.server.exceptions import PulpCodedException

from pulp_ostree.plugins.lib import LibError
from pulp_ostree.plugins.importers.steps import Main, Create, Pull, Add, Clean, Remote
from pulp_ostree.common.model import Unit
from pulp_ostree.common import constants, errors


# The module being tested
MODULE = 'pulp_ostree.plugins.importers.steps'


class TestMainStep(TestCase):

    @patch('pulp_ostree.common.model.generate_remote_id')
    def test_init(self, fake_generate):
        repo = Mock()
        conduit = Mock()
        working_dir = 'dir-123'
        url = 'url-123'
        branches = ['branch-1', 'branch-2']
        digest = 'digest-123'
        fake_generate.return_value = digest
        config = {
            importer_constants.KEY_FEED: url,
            constants.IMPORTER_CONFIG_KEY_BRANCHES: branches
        }

        # test
        step = Main(repo=repo, conduit=conduit, config=config, working_dir=working_dir)

        # validation
        self.assertEqual(step.step_id, constants.IMPORT_STEP_MAIN)
        self.assertEqual(step.repo, repo)
        self.assertEqual(step.conduit, conduit)
        self.assertEqual(step.config, config)
        self.assertEqual(step.working_dir, working_dir)
        self.assertEqual(step.plugin_type, constants.WEB_IMPORTER_TYPE_ID)
        self.assertEqual(step.feed_url, url)
        self.assertEqual(step.remote_id, digest)
        self.assertEqual(step.branches, branches)
        self.assertEqual(step.storage_path,
                         os.path.join(constants.SHARED_STORAGE, digest, 'content'))

        self.assertEqual(len(step.children), 4)
        self.assertTrue(isinstance(step.children[0], Create))
        self.assertTrue(isinstance(step.children[1], Pull))
        self.assertTrue(isinstance(step.children[2], Add))
        self.assertTrue(isinstance(step.children[3], Clean))


class TestCreate(TestCase):

    def test_init(self):
        step = Create()
        self.assertEqual(step.step_id, constants.IMPORT_STEP_CREATE_REPOSITORY)
        self.assertTrue(step.description is not None)

    @patch(MODULE + '.lib')
    @patch(MODULE + '.Remote')
    def test_init_repository(self, fake_remote, fake_lib):
        url = 'url-123'
        remote_id = 'remote-123'
        repo_id = 'repo-123'
        path = 'root/path-123'

        fake_lib.LibError = LibError
        fake_lib.Repository.return_value.open.side_effect = LibError

        # test
        step = Create()
        step.parent = Mock(feed_url=url, remote_id=remote_id, repo_id=repo_id)
        step._init_repository(path)

        # validation
        fake_remote.assert_called_once_with(step, fake_lib.Repository.return_value)
        fake_lib.Repository.assert_called_once_with(path)
        fake_lib.Repository.return_value.open.assert_called_once_with()
        fake_lib.Repository.return_value.create.assert_called_once_with()
        fake_remote.return_value.add.assert_called_once_with()

    @patch(MODULE + '.lib')
    @patch(MODULE + '.Remote')
    def test_init_repository_exists(self, fake_remote, fake_lib):
        url = 'url-123'
        remote_id = 'remote-123'
        repo_id = 'repo-xyz'
        path = 'root/path-123'

        # test
        step = Create()
        step.parent = Mock(feed_url=url, remote_id=remote_id, repo_id=repo_id)
        step._init_repository(path)

        # validation
        fake_remote.assert_called_once_with(step, fake_lib.Repository.return_value)
        fake_lib.Repository.assert_called_once_with(path)
        fake_lib.Repository.return_value.open.assert_called_once_with()
        fake_remote.return_value.add.assert_called_once_with()

    @patch(MODULE + '.lib')
    def test_init_repository_exception(self, fake_lib):
        fake_lib.LibError = LibError
        fake_lib.Repository.side_effect = LibError
        try:
            step = Create()
            step.parent = Mock(feed_url='', remote_id='')
            step._init_repository('')
            self.assertTrue(False, msg='Create exception expected')
        except PulpCodedException, pe:
            self.assertEqual(pe.error_code, errors.OST0001)

    @patch(MODULE + '.mkdir')
    def test_process_main(self, fake_mkdir):
        url = 'url-123'
        remote_id = 'remote-123'
        path = 'root/path-123'

        # test
        step = Create()
        step.parent = Mock(storage_path=path, feed_url=url, remote_id=remote_id)
        step._init_repository = Mock()
        step.process_main()

        # validation
        self.assertEqual(
            fake_mkdir.call_args_list,
            [
                ((path,), {}),
                ((os.path.join(os.path.dirname(path), constants.LINKS_DIR),), {})
            ])
        step._init_repository.assert_called_with(path)


class TestPull(TestCase):

    def test_init(self):
        step = Pull()
        self.assertEqual(step.step_id, constants.IMPORT_STEP_PULL)
        self.assertTrue(step.description is not None)

    def test_process_main(self):
        repo_id = 'repo-xyz'
        path = 'root/path-123'
        branches = ['branch-1', 'branch-2']

        # test
        step = Pull()
        step.parent = Mock(storage_path=path, repo_id=repo_id, branches=branches)
        step._pull = Mock()
        step.process_main()

        # validation
        self.assertEqual(
            step._pull.call_args_list,
            [
                ((path, repo_id, branches[0]), {}),
                ((path, repo_id, branches[1]), {}),
            ])

    @patch(MODULE + '.lib')
    def test_pull(self, fake_lib):
        remote_id = 'remote-123'
        path = 'root/path-123'
        branch = 'branch-1'
        repo = Mock()
        fake_lib.Repository.return_value = repo
        report = Mock(fetched=1, requested=2, percent=50)

        def fake_pull(remote_id, branch, listener):
            listener(report)

        repo.pull.side_effect = fake_pull

        # test
        step = Pull()
        step.report_progress = Mock()
        step._pull(path, remote_id, branch)

        # validation
        fake_lib.Repository.assert_called_once_with(path)
        repo.pull.assert_called_once_with(remote_id, [branch], ANY)
        step.report_progress.assert_called_with(force=True)
        self.assertEqual(step.progress_details, 'branch: branch-1 fetching 1/2 50%')

    @patch(MODULE + '.lib')
    def test_pull_raising_exception(self, fake_lib):
        fake_lib.LibError = LibError
        fake_lib.Repository.return_value.pull.side_effect = LibError
        try:
            step = Pull()
            step._pull('', '', '')
            self.assertTrue(False, msg='Pull exception expected')
        except PulpCodedException, pe:
            self.assertEqual(pe.error_code, errors.OST0002)


class TestAdd(TestCase):

    def test_init(self):
        step = Add()
        self.assertEqual(step.step_id, constants.IMPORT_STEP_ADD_UNITS)
        self.assertTrue(step.description is not None)

    @patch(MODULE + '.lib')
    @patch(MODULE + '.model')
    @patch(MODULE + '.Add.link')
    @patch(MODULE + '.Unit')
    def test_process_main(self, fake_unit, fake_link, fake_model, fake_lib):
        remote_id = 'remote-1'
        commits = [
            Mock(),
            Mock()
        ]
        refs = [
            Mock(path='branch:1', commit='commit:1', metadata='md:1'),
            Mock(path='branch:2', commit='commit:2', metadata='md:2'),
            Mock(path='branch:3', commit='commit:3', metadata='md:3')
        ]
        units = [
            Mock(key='key:1', metadata=refs[0].metadata, storage_path='path:1'),
            Mock(key='key:2', metadata=refs[1].metadata, storage_path='path:2')
        ]
        pulp_units = [
            Mock(),
            Mock()
        ]

        branches = [r.path for r in refs[:-1]]

        repository = Mock()
        repository.list_refs.return_value = refs
        fake_lib.Repository.return_value = repository

        fake_model.Commit.side_effect = commits
        fake_model.Unit.side_effect = units

        fake_unit.side_effect = pulp_units

        fake_conduit = Mock()

        # test
        step = Add()
        step.parent = Mock(remote_id=remote_id, storage_path='/tmp/xyz', branches=branches)
        step.get_conduit = Mock(return_value=fake_conduit)
        step.process_main()

        # validation
        fake_lib.Repository.assert_called_once_with(step.parent.storage_path)
        self.assertEqual(
            fake_model.Commit.call_args_list,
            [
                (('commit:1', 'md:1'), {}),
                (('commit:2', 'md:2'), {}),
            ])
        self.assertEqual(
            fake_model.Unit.call_args_list,
            [
                ((remote_id, 'branch:1', commits[0]), {}),
                ((remote_id, 'branch:2', commits[1]), {}),
            ])
        self.assertEqual(
            fake_link.call_args_list,
            [
                ((units[0],), {}),
                ((units[1],), {}),
            ])
        self.assertEqual(
            fake_unit.call_args_list,
            [
                ((Unit.TYPE_ID, units[0].key, units[0].metadata, units[0].storage_path), {}),
                ((Unit.TYPE_ID, units[1].key, units[1].metadata, units[1].storage_path), {}),
            ])
        self.assertEqual(
            fake_conduit.save_unit.call_args_list,
            [
                ((pulp_units[0],), {}),
                ((pulp_units[1],), {}),
            ])

    @patch('os.symlink')
    def test_link(self, fake_link):
        target = 'path-1'
        link_path = 'path-2'
        step = Add()
        unit = Mock(storage_path=link_path)
        step.parent = Mock(storage_path=target)
        step.link(unit)
        fake_link.assert_called_with(target, link_path)

    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('os.symlink')
    def test_link_exists(self, fake_link, fake_islink, fake_readlink):
        target = 'path-1'
        link_path = 'path-2'
        step = Add()
        unit = Mock(storage_path=link_path)
        step.parent = Mock(storage_path=target)
        fake_islink.return_value = True
        fake_readlink.return_value = target
        fake_link.side_effect = OSError(errno.EEXIST, link_path)

        # test
        step.link(unit)

        # validation
        fake_islink.assert_called_with(link_path)
        fake_readlink.assert_called_with(link_path)

    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('os.symlink')
    def test_link_exists_not_link(self, fake_link, fake_islink, fake_readlink):
        target = 'path-1'
        link_path = 'path-2'
        step = Add()
        unit = Mock(storage_path=link_path)
        step.parent = Mock(storage_path=target)
        fake_islink.return_value = False
        fake_readlink.return_value = target
        fake_link.side_effect = OSError(errno.EEXIST, link_path)

        # test
        self.assertRaises(OSError, step.link, unit)

        # validation
        fake_islink.assert_called_with(link_path)
        self.assertFalse(fake_readlink.called)

    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('os.symlink')
    def test_link_exists_wrong_target(self, fake_link, fake_islink, fake_readlink):
        target = 'path-1'
        link_path = 'path-2'
        step = Add()
        unit = Mock(storage_path=link_path)
        step.parent = Mock(storage_path=target)
        fake_islink.return_value = True
        fake_readlink.return_value = 'not-target'
        fake_link.side_effect = OSError(errno.EEXIST, link_path)

        # test
        self.assertRaises(OSError, step.link, unit)

        # validation
        fake_islink.assert_called_with(link_path)
        fake_readlink.assert_called_with(link_path)

    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('os.symlink')
    def test_link_error(self, fake_link, fake_islink, fake_readlink):
        target = 'path-1'
        link_path = 'path-2'
        step = Add()
        unit = Mock(storage_path=link_path)
        step.parent = Mock(storage_path=target)
        fake_link.side_effect = OSError(errno.EPERM, link_path)

        # test
        self.assertRaises(OSError, step.link, unit)

        # validation
        self.assertFalse(fake_islink.called)
        self.assertFalse(fake_readlink.called)


class TestClean(TestCase):

    def test_init(self):
        step = Clean()
        self.assertEqual(step.step_id, constants.IMPORT_STEP_CLEAN)
        self.assertTrue(step.description is not None)

    @patch(MODULE + '.lib')
    def test_process_main(self, fake_lib):
        path = 'root/path-123'
        repo_id = 'repo-123'

        # test
        step = Clean()
        step.parent = Mock(storage_path=path, repo_id=repo_id)
        step.process_main()

        # validation
        fake_lib.Repository.assert_called_once_with(path)
        fake_lib.Remote.assert_called_once_with(repo_id, fake_lib.Repository.return_value)
        fake_lib.Remote.return_value.delete.assert_called_once_with()

    @patch(MODULE + '.lib')
    def test_process_main_exception(self, fake_lib):
        path = 'root/path-123'
        importer_id = 'importer-xyz'

        fake_lib.LibError = LibError
        fake_lib.Remote.return_value.delete.side_effect = LibError

        # test
        try:
            step = Clean()
            step.parent = Mock(storage_path=path, importer_id=importer_id)
            step.process_main()
            self.assertTrue(False, msg='Delete remote exception expected')
        except PulpCodedException, pe:
            self.assertEqual(pe.error_code, errors.OST0003)


class TestRemote(TestCase):

    def test_init(self):
        step = Mock()
        repository = Mock()
        remote = Remote(step, repository)
        self.assertEqual(remote.step, step)
        self.assertEqual(remote.repository, repository)

    def test_url(self):
        step = Mock()
        step.parent = Mock(feed_url='http://')
        remote = Remote(step, None)
        self.assertEqual(remote.url, step.parent.feed_url)

    def test_remote_id(self):
        step = Mock()
        step.parent = Mock(repo_id='123')
        remote = Remote(step, None)
        self.assertEqual(remote.remote_id, step.parent.repo_id)

    def test_working_dir(self):
        step = Mock()
        remote = Remote(step, None)
        self.assertEqual(remote.working_dir, step.get_working_dir.return_value)

    def test_config(self):
        step = Mock()
        remote = Remote(step, None)
        self.assertEqual(remote.config, step.get_config.return_value)

    @patch('os.chmod')
    @patch('__builtin__.open')
    def test_ssl_key_path(self, fake_open, fake_chmod):
        key = 'test-key'
        config = {
            importer_constants.KEY_SSL_CLIENT_KEY: key
        }
        working_dir = '/tmp/test'
        step = Mock()
        step.get_config.return_value = config
        step.get_working_dir.return_value = working_dir
        fp = Mock(__enter__=Mock(), __exit__=Mock())
        fp.__enter__.return_value = fp
        fake_open.return_value = fp

        # test
        remote = Remote(step, None)
        path = remote.ssl_key_path

        # validation
        expected_path = os.path.join(working_dir, 'key.pem')
        fake_open.assert_called_once_with(expected_path, 'w+')
        fp.write.assert_called_once_with(key)
        fp.__enter__.assert_called_once_with()
        fp.__exit__.assert_called_once_with(None, None, None)
        fake_chmod.assert_called_once_with(expected_path, 0600)
        self.assertEqual(path, expected_path)

    @patch('__builtin__.open')
    def test_ssl_cert_path(self, fake_open):
        cert = 'test-key'
        config = {
            importer_constants.KEY_SSL_CLIENT_CERT: cert
        }
        working_dir = '/tmp/test'
        step = Mock()
        step.get_config.return_value = config
        step.get_working_dir.return_value = working_dir
        fp = Mock(__enter__=Mock(), __exit__=Mock())
        fp.__enter__.return_value = fp
        fake_open.return_value = fp

        # test
        remote = Remote(step, None)
        path = remote.ssl_cert_path

        # validation
        expected_path = os.path.join(working_dir, 'cert.pem')
        fake_open.assert_called_once_with(expected_path, 'w+')
        fp.write.assert_called_once_with(cert)
        fp.__enter__.assert_called_once_with()
        fp.__exit__.assert_called_once_with(None, None, None)
        self.assertEqual(path, expected_path)

    @patch('__builtin__.open')
    def test_ssl_ca_path(self, fake_open):
        cert = 'test-key'
        config = {
            importer_constants.KEY_SSL_CA_CERT: cert
        }
        working_dir = '/tmp/test'
        step = Mock()
        step.get_config.return_value = config
        step.get_working_dir.return_value = working_dir
        fp = Mock(__enter__=Mock(), __exit__=Mock())
        fp.__enter__.return_value = fp
        fake_open.return_value = fp

        # test
        remote = Remote(step, None)
        path = remote.ssl_ca_path

        # validation
        expected_path = os.path.join(working_dir, 'ca.pem')
        fake_open.assert_called_once_with(expected_path, 'w+')
        fp.write.assert_called_once_with(cert)
        fp.__enter__.assert_called_once_with()
        fp.__exit__.assert_called_once_with(None, None, None)
        self.assertEqual(path, expected_path)

    def test_ssl_validation(self):
        config = {
            importer_constants.KEY_SSL_VALIDATION: True
        }
        step = Mock()
        step.get_config.return_value = config

        # test
        remote = Remote(step, None)
        validation = remote.ssl_validation

        # validation
        self.assertTrue(validation)
        self.assertTrue(isinstance(validation, bool))

    def test_ssl_validation_not_specified(self):
        config = {}
        step = Mock()
        step.get_config.return_value = config

        # test
        remote = Remote(step, None)
        validation = remote.ssl_validation

        # validation
        self.assertFalse(validation)
        self.assertTrue(isinstance(validation, bool))

    @patch(MODULE + '.GPG')
    def test_gpg_key(self, fake_gpg):
        keys = [1, 2, 3]
        key_list = [dict(keyid=k) for k in keys]
        working_dir = '/tmp/test'
        config = {
            constants.IMPORTER_CONFIG_KEY_GPG_KEYS: keys
        }
        step = Mock()
        step.get_config.return_value = config
        step.get_working_dir.return_value = working_dir

        fake_gpg.return_value.list_keys.return_value = key_list

        # test
        remote = Remote(step, None)
        path, key_ids = remote.gpg_keys

        # validation
        fake_gpg.assert_called_once_with(gnupghome=working_dir)
        self.assertEqual(
            fake_gpg.return_value.import_keys.call_args_list,
            [((k,), {}) for k in keys])
        self.assertEqual(path, os.path.join(working_dir, 'pubring.gpg'))
        self.assertEqual(key_ids, [k['keyid'] for k in key_list])

    def test_proxy_url(self):
        host = 'proxy-host'
        port = 'proxy-port'
        user = 'proxy-user'
        password = 'proxy-password'
        config = {
            importer_constants.KEY_PROXY_HOST: host,
            importer_constants.KEY_PROXY_PORT: port,
            importer_constants.KEY_PROXY_USER: user,
            importer_constants.KEY_PROXY_PASS: password,
        }
        step = Mock()
        step.get_config.return_value = config

        proxy_url = '@'.join(
            (':'.join((user, password)),
             ':'.join((host, port))))

        # test
        remote = Remote(step, None)

        # validation
        self.assertEqual(remote.proxy_url, proxy_url)

    @patch(MODULE + '.lib')
    @patch(MODULE + '.Remote.url', PropertyMock())
    @patch(MODULE + '.Remote.remote_id', PropertyMock())
    @patch(MODULE + '.Remote.ssl_key_path', PropertyMock())
    @patch(MODULE + '.Remote.ssl_cert_path', PropertyMock())
    @patch(MODULE + '.Remote.ssl_ca_path', PropertyMock())
    @patch(MODULE + '.Remote.ssl_validation', PropertyMock())
    @patch(MODULE + '.Remote.proxy_url', PropertyMock())
    @patch(MODULE + '.Remote.gpg_keys', new_callable=PropertyMock)
    def test_add(self, fake_gpg, fake_lib):
        step = Mock()
        repository = Mock()
        path = Mock()
        key_ids = [1, 2, 3]
        fake_gpg.return_value = (path, key_ids)

        # test
        remote = Remote(step, repository)
        remote.add()

        # validation
        fake_lib.Remote.assert_called_once_with(remote.remote_id, repository)
        fake_lib.Remote.return_value.update.assert_called_once_with()
        fake_lib.Remote.return_value.import_key.assert_called_once_with(path, key_ids)
        self.assertEqual(fake_lib.Remote.return_value.url, remote.url)
        self.assertEqual(fake_lib.Remote.return_value.ssl_key_path, remote.ssl_key_path)
        self.assertEqual(fake_lib.Remote.return_value.ssl_cert_path, remote.ssl_cert_path)
        self.assertEqual(fake_lib.Remote.return_value.ssl_ca_path, remote.ssl_ca_path)
        self.assertEqual(fake_lib.Remote.return_value.ssl_validation, remote.ssl_validation)
        self.assertEqual(fake_lib.Remote.return_value.proxy_url, remote.proxy_url)
        self.assertTrue(fake_lib.Remote.return_value.gpg_validation, remote.ssl_validation)
