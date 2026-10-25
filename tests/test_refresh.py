import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import refresh
import cli
spec=importlib.util.spec_from_file_location('lol_fetch',ROOT/'games/lol/fetch.py')
lol=importlib.util.module_from_spec(spec); spec.loader.exec_module(lol)

class RefreshTests(unittest.TestCase):
    def test_drive_html_spacing_and_attribute_order(self):
        parser=lol.FolderParser()
        parser.feed('<div id="entry-first">'+' '*1000+'<div class="other flip-entry-title">2026_LoL_esports.csv</div></div><div id="entry-second"><div class="flip-entry-title">2025_LoL.csv</div></div>')
        self.assertEqual(parser.files,{'2026':'first','2025':'second'})
    def test_empty_folder_fails(self):
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock();response.read.return_value=b'<html>error</html>'
        with patch.object(lol.urllib.request,'urlopen',return_value=response):
            with self.assertRaises(RuntimeError): lol.list_folder()
    def test_refused_snapshot_preserves_old_data_and_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)/'games/lol';d.mkdir(parents=True);snap=d/'ratings.json';snap.write_text('{"n_teams":308}')
            ad=Mock();ad.load.return_value=[]
            with patch.object(cli,'ROOT',tmp),patch.object(cli,'adapter',return_value=ad),patch.object(cli,'cfg',return_value={'name':'LoL'}):
                with self.assertRaises(RuntimeError): cli.cmd_snapshot('lol')
            self.assertEqual(json.loads(snap.read_text())['n_teams'],308)
    def test_partial_failure_has_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(refresh,'ROOT',tmp),patch.object(sys,'argv',['refresh.py','lol','cod']),patch.object(refresh,'refresh',side_effect=['fail','ok']):
            with self.assertRaises(SystemExit): refresh.main()
            self.assertEqual(json.loads((Path(tmp)/'refresh-status.json').read_text())['games']['lol'],'fail')
    def test_unknown_game_is_error(self):
        with patch.object(sys,'argv',['refresh.py','typo']):
            with self.assertRaises(SystemExit): refresh.main()

if __name__=='__main__': unittest.main()
