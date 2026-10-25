import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sources import pandascore as p

class PandaScoreTests(unittest.TestCase):
    def test_individual_player_scores_keep_winner_and_opponent_identity(self):
        match = self.match(12, '2026-10-24')
        match['results'] = [{'player_id':1,'score':3}, {'player_id':2,'score':1}]
        row = p.extract(match)
        self.assertEqual((row['t1'], row['t2'], row['s1'], row['s2'], row['w']),
                         ('A', 'B', 3, 1, 1))

    def match(self,identifier,date):
        return {'id':identifier,'begin_at':date+'T12:00:00Z','opponents':[{'opponent':{'id':1,'name':'A'}},{'opponent':{'id':2,'name':'B'}}],
                'results':[{'team_id':1,'score':2},{'team_id':2,'score':0}],'winner_id':1,'number_of_games':3,'league':{'name':'Major'}}
    def test_new_results_spanning_multiple_pages_are_not_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'matches.json';file.write_text(json.dumps([p.extract(self.match(1,'2026-10-20'))]))
            file.with_suffix('.complete.json').write_text('{"cutoff":"2025-01-01"}')
            pages=[[self.match(i,'2026-10-24') for i in range(2,102)],
                   [self.match(i,'2026-10-23') for i in range(102,202)],
                   [self.match(202,'2026-10-16')]]
            with patch.object(p.time,'sleep'):
                p.collect('csgo',file,'2025-01-01','secret',fetch=lambda *args:pages.pop(0))
            self.assertEqual(len(json.loads(file.read_text())),202)
            self.assertFalse(pages)
    def test_mid_batch_failure_preserves_complete_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'matches.json';file.write_text(json.dumps([p.extract(self.match(1,'2026-10-20'))]))
            previous=file.read_bytes()
            def fetch(*args):
                if fetch.calls:
                    raise RuntimeError('HTTP 429')
                fetch.calls+=1
                return [self.match(i,'2026-10-24') for i in range(2,102)]
            fetch.calls=0
            with patch.object(p.time,'sleep'):
                with self.assertRaises(RuntimeError):p.collect('csgo',file,'2025-01-01','secret',fetch=fetch)
            self.assertEqual(previous,file.read_bytes())
    def test_rate_limit_is_explicit_and_not_empty_success(self):
        error=urllib.error.HTTPError('https://api.pandascore.co',429,'Too Many Requests',{'X-Rate-Limit-Reset':'123'},None)
        with patch.object(p.urllib.request,'urlopen',side_effect=error):
            with self.assertRaisesRegex(RuntimeError,'HTTP 429.*123'):p.api('/videogames','secret')
    def test_non_list_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'matches.json'
            with self.assertRaises(RuntimeError):p.collect('csgo',path,'2025-01-01','secret',fetch=lambda *args:{'error':'bad'})
            self.assertFalse(path.exists())

if __name__=='__main__':unittest.main()
