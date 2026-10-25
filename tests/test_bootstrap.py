import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('bootstrap', Path(__file__).resolve().parents[1] / 'deploy/export-vps-bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / 'games/lol/data/example.csv'
        self.cache.parent.mkdir(parents=True)
        self.cache.write_text('public-source-fixture')

    def test_only_recipient_can_decrypt_and_cache_excludes_secrets(self):
        private = self.root / 'private.pem'
        subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(private)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        public = subprocess.check_output(['openssl','pkey','-in',str(private),'-pubout'],text=True)
        (self.cache.parent / '.env').write_text('must-not-be-exported')
        out = self.root / 'export'
        self.assertEqual(bootstrap.export(self.root,out,public,'dummy-free-token'),1)
        clear = subprocess.check_output(['openssl','pkeyutl','-decrypt','-inkey',str(private),
                  '-pkeyopt','rsa_padding_mode:oaep','-pkeyopt','rsa_oaep_md:sha256','-in',str(out/'refresh-config.enc')])
        self.assertEqual(json.loads(clear),{'PANDASCORE_TOKEN':'dummy-free-token'})
        self.assertNotIn(b'dummy-free-token',(out/'refresh-config.enc').read_bytes())
        with tarfile.open(out/'source-cache.tar.gz') as archive:
            self.assertEqual(archive.getnames(),['games/lol/data/example.csv'])
        self.assertEqual({p.name for p in out.iterdir()},{'refresh-config.enc','source-cache.tar.gz'})

    def test_missing_credentials_cannot_create_export(self):
        with self.assertRaises(ValueError):bootstrap.export(self.root,self.root/'out','','dummy')
        self.assertFalse((self.root/'out').exists())

    def test_cache_symlink_cannot_export_other_files(self):
        self.cache.unlink();self.cache.symlink_to(self.root/'private.pem')
        with self.assertRaisesRegex(ValueError,'symlink'):
            bootstrap.export(self.root,self.root/'out','public-key','dummy')
