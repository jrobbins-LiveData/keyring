"""
test_core.py

Created by Kang Zhang on 2009-08-09
"""

from __future__ import with_statement

import os
import tempfile
import shutil

import mock
import pytest

import keyring.backend
import keyring.core
import keyring.util.platform_
from keyring import errors

PASSWORD_TEXT = "This is password"
PASSWORD_TEXT_2 = "This is password2"


@pytest.yield_fixture()
def config_filename(tmpdir):
    filename = tmpdir / 'keyringrc.cfg'
    with mock.patch('keyring.util.platform_.config_root', lambda: str(tmpdir)):
        yield str(filename)


class TestKeyring(keyring.backend.KeyringBackend):
    """A faked keyring for test.
    """
    def __init__(self):
        self.passwords = {}

    def supported(self):
        return 0

    def get_password(self, service, username):
        return PASSWORD_TEXT

    def set_password(self, service, username, password):
        self.passwords[(service, username)] = password
        return 0

    def delete_password(self, service, username):
        try:
            del self.passwords[(service, username)]
        except KeyError:
            raise errors.PasswordDeleteError("not set")


class TestKeyring2(TestKeyring):
    """Another faked keyring for test.
    """
    def get_password(self, service, username):
        return PASSWORD_TEXT_2


class TestCore:
    mock_global_backend = mock.patch('keyring.core._keyring_backend')

    @mock_global_backend
    def test_set_password(self, backend):
        """
        set_password on the default keyring is called.
        """
        keyring.core.set_password("test", "user", "passtest")
        backend.set_password.assert_called_once_with('test', 'user',
            'passtest')

    @mock_global_backend
    def test_get_password(self, backend):
        """
        set_password on the default keyring is called.
        """
        result = keyring.core.get_password("test", "user")
        backend.get_password.assert_called_once_with('test', 'user')
        assert result is not None

    @mock_global_backend
    def test_delete_password(self, backend):
        keyring.core.delete_password("test", "user")
        backend.delete_password.assert_called_once_with('test', 'user')

    def test_set_keyring_in_runtime(self):
        """Test the function of set keyring in runtime.
        """
        keyring.core.set_keyring(TestKeyring())

        keyring.core.set_password("test", "user", "password")
        assert keyring.core.get_password("test", "user") == PASSWORD_TEXT

    def test_set_keyring_in_config(self, config_filename):
        """Test setting the keyring by config file.
        """
        # create the config file
        with open(config_filename, 'w') as config_file:
            config_file.writelines([
                "[backend]\n",
                # the path for the user created keyring
                "keyring-path= %s\n" % os.path.dirname(os.path.abspath(__file__)),
                # the name of the keyring class
                "default-keyring=test_core.TestKeyring2\n",
                ])

        # init the keyring lib, the lib will automaticlly load the
        # config file and load the user defined module
        keyring.core.init_backend()

        keyring.core.set_password("test", "user", "password")
        assert keyring.core.get_password("test", "user") == PASSWORD_TEXT_2

    def test_load_config(self):
        tempdir = tempfile.mkdtemp()
        old_location = os.getcwd()
        os.chdir(tempdir)
        personal_cfg = os.path.join(os.path.expanduser("~"), "keyringrc.cfg")
        if os.path.exists(personal_cfg):
            os.rename(personal_cfg, personal_cfg + '.old')
            personal_renamed = True
        else:
            personal_renamed = False

        # loading with an empty environment
        keyring.core.load_config()

        # loading with a file that doesn't have a backend section
        cfg = os.path.join(tempdir, "keyringrc.cfg")
        f = open(cfg, 'w')
        f.write('[keyring]')
        f.close()
        keyring.core.load_config()

        # loading with a file that doesn't have a default-keyring value
        cfg = os.path.join(tempdir, "keyringrc.cfg")
        f = open(cfg, 'w')
        f.write('[backend]')
        f.close()
        keyring.core.load_config()

        os.chdir(old_location)
        shutil.rmtree(tempdir)
        if personal_renamed:
            os.rename(personal_cfg + '.old', personal_cfg)
