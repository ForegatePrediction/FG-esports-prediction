"""PandaScore free Fixtures collector: atomic output and cached incremental replay."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request


def api(path, token):
    request = urllib.request.Request('https://api.pandascore.co' + path,
                                    headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'})
    last = 'unknown request error'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if 'page[number]=1' in path or path == '/videogames':
                    quota = {k: v for k, v in response.headers.items() if 'ratelimit' in k.lower().replace('-', '') or k.lower() == 'retry-after'}
                    print('[quota]', json.dumps(quota), flush=True)
                result = json.load(response)
            if not isinstance(result, list):
                raise RuntimeError('PandaScore response is not a match list')
            return result
        except urllib.error.HTTPError as error:
            quota = {k: v for k, v in error.headers.items() if 'ratelimit' in k.lower().replace('-', '') or k.lower() == 'retry-after'}
            last = 'HTTP {} {}'.format(error.code, json.dumps(quota))
            if error.code in (401, 403, 404, 429):
                raise RuntimeError('PandaScore ' + last) from None
        except (OSError, ValueError) as error:
            last = type(error).__name__
        if attempt < 2:
            time.sleep(1 + attempt)
    raise RuntimeError('PandaScore retries exhausted: ' + last)


def extract(match):
    opponents = match.get('opponents') or []
    if len(opponents) != 2:
        return None
    a, b = [x['opponent'] for x in opponents]
    scores = {(x.get('team_id') or x.get('player_id')): x.get('score')
              for x in (match.get('results') or [])}
    return {'id': match['id'], 'date': (match.get('begin_at') or '')[:10],
            't1': a['name'], 't2': b['name'], 's1': scores.get(a['id']), 's2': scores.get(b['id']),
            'bo': match.get('number_of_games'),
            'w': 1 if match.get('winner_id') == a['id'] else 2 if match.get('winner_id') == b['id'] else None,
            'league': (match.get('league') or {}).get('name'),
            'tournament': (match.get('tournament') or {}).get('name'),
            'series': (match.get('serie') or {}).get('full_name')}


def collect(game, path, cutoff, token, fetch=api, test=False):
    path = Path(path)
    marker = path.with_suffix('.complete.json')
    stored = json.loads(path.read_text()) if path.exists() else []
    rows = {row['id']: row for row in stored}
    complete = json.loads(marker.read_text()) if marker.exists() else {}
    latest = max((x['date'] for x in stored if x.get('date')), default='')
    # A complete cache is necessary. A partial file must never hide missing history.
    boundary = (dt.date.fromisoformat(latest) - dt.timedelta(days=3)).isoformat() if latest and complete.get('cutoff') == cutoff else cutoff
    finished = False
    for page in range(1, (1 if test else 400) + 1):
        batch = fetch(f'/{game}/matches/past?filter[status]=finished&sort=-begin_at&page[size]=100&page[number]={page}', token)
        if not isinstance(batch, list):
            raise RuntimeError('PandaScore response is not a match list')
        if not batch:
            finished = True
            break
        dates = []
        for match in batch:
            date = (match.get('begin_at') or '')[:10]
            if date:
                dates.append(date)
            row = extract(match)
            if row:
                rows[row['id']] = row
        oldest = min(dates, default='')
        print(f'[fetch] {game} page={page} rows={len(rows)} oldest={oldest} boundary={boundary}', flush=True)
        if oldest and oldest < boundary or len(batch) < 100:
            finished = True
            break
        if test:
            break
        time.sleep(.2)
    if not finished and not test:
        raise RuntimeError('PandaScore page cap reached before history boundary; refuse incomplete snapshot')
    if not rows:
        raise RuntimeError('PandaScore returned no usable matches')
    # Commit only after the complete batch; failures preserve both cached and live data.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(list(rows.values()), ensure_ascii=False))
    os.replace(temporary, path)
    if not test:
        marker.write_text(json.dumps({'cutoff': cutoff}))
    print('source_latest_match_date=' + max(x['date'] for x in rows.values() if x.get('date')))


def main(game, filename, cutoff, directory):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', default=game)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--list-games', action='store_true')
    parser.add_argument('cutoff', nargs='?', default=cutoff)
    args = parser.parse_args()
    token = os.environ.get('PANDASCORE_TOKEN')
    if not token:
        raise RuntimeError('Missing PANDASCORE_TOKEN (free Fixtures authentication)')
    if args.list_games:
        for row in api('/videogames', token):
            print(row.get('slug'), row.get('name'))
        return
    collect(args.game, Path(directory)/filename, args.cutoff, token, test=args.test)


if __name__ == '__main__':
    token = os.environ.get('PANDASCORE_TOKEN')
    if not token:
        sys.exit('Missing PANDASCORE_TOKEN')
    games = api('/videogames', token)
    print('Free Fixtures authentication successful; videogames:', len(games))
