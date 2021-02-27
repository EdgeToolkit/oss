import os
import unittest
from ci import GitlabRunner

_DIR = os.path.dirname(__file__)
_TOP = f"{_DIR}/../.."
_DB = f"{_TOP}/.ansible/config/tokens.yml"

_REGISTRATION_TOKEN = None
_PRIVATE_TOKEN = 'kypLygrDSZ-92NewWx4R'
_GITLAB_URL = 'http://172.16.0.121:8200'


class Test1(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        pass

    @classmethod
    def tearDownClass(self):
        pass

    def setUp(self):
        gl = GitlabRunner(_GITLAB_URL, _PRIVATE_TOKEN, _DB)
        gl.reset()
        for rid in gl.db.token:
            runner = gl.gitlab.runners.get(rid)
            self.assertEqual(gl.FREE_FORMAT.format(id=rid), runner.description)

    def tearDown(self):
        pass

    def test_one(self):
        print('execute test_one')

#    def test_two(self):
#        print('execute test_two')


if __name__ == '__main__':
    unittest.main()
