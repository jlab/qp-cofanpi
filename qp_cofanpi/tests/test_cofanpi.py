from unittest import main
from os import close, remove, chmod, environ
from shutil import copyfile, rmtree
from tempfile import mkstemp, mkdtemp
from json import dumps, load
from os.path import exists, isdir, join
from os import environ

from qiita_client.testing import PluginTestCase

from qp_cofanpi import plugin
from qp_cofanpi.cofanpi import (cofanpi, OUT_NAME_withRNA, OUT_NAME_noRNA)


class cofanpiTests(PluginTestCase):
    def setUp(self):
        # this will allow us to see the full errors
        self.maxDiff = None

        plugin("https://localhost:8383", 'register', 'ignored')
        self.params = {
            'antiSMASH database': environ.get('QP_COFANPI_DBVERSION_ANTISMASH', 'unknown'),
            'CARD database': environ.get('QP_COFANPI_DBVERSION_CARD', 'unknown'),
            'EggNOG database': environ.get('QP_COFANPI_DBVERSION_EGGNOG', 'unknown'),
            'InterProScan database': environ.get('QP_COFANPI_DBVERSION_IPRSCAN', 'unknown')}
        
        self._clean_up_files = []

        # saving current value of PATH
        self.oldpath = environ['PATH']

    def tearDown(self):
        # restore eventually changed PATH env var
        environ['PATH'] = self.oldpath
        for fp in self._clean_up_files:
            if exists(fp):
                if isdir(fp):
                    rmtree(fp)
                else:
                    remove(fp)

    def test_cofanpi(self):
        # TODO: write some meaningful tests!
        pass


if __name__ == '__main__':
    main()
