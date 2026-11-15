#!/usr/bin/env python3
"""Fetch German RSS headlines and short summaries for a static learning app."""
import datetime as dt
import email.utils
import json
import pathlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import re
import html

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'news.json'
SEARCHES = {
    'Politik': ['Bundestag Bundesregierung Politik', 'Europäische Union Politik'],
    'Wirtschaft': ['Wirtschaft Deutschland Unternehmen', 'Arbeitsmarkt Konjunktur Deutschland'],
    'Technologie': ['Künstliche Intelligenz Technologie', 'Digitalisierung Cybersicherheit'],
    'Wissenschaft': ['Wissenschaft Forschung Deutschland', 'Forschung Universität Entdeckung'],
    'Gesundheit': ['Medizin Gesundheit Forschung', 'Gesundheitssystem Deutschland'],
    'International': ['Internationale Politik Welt', 'Europa internationale Beziehungen'],
}


def clean(value):
    value = re.sub(r'<[^>]*>', ' ', value or '')
    return re.sub(r'\s+', ' ', html.unescape(value)).strip()


def download(query):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({
        'q': query + ' when:7d', 'hl': 'de', 'gl': 'DE', 'ceid': 'DE:de'
    })
    request = urllib.request.Request(url, headers={'User-Agent': 'DeutschLernenNewsBot/1.0 (RSS educational reader)'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def main():
    now = dt.datetime.now(dt.timezone.utc)
    prior = {}
    if OUT.exists():
        try:
            prior = json.loads(OUT.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            pass
    previous = prior.get('items', [])
    items = []
    failures = []
    for category, queries in SEARCHES.items():
        seen = set()
        for query in queries:
            try:
                root = ET.fromstring(download(query))
                for entry in root.findall('.//item'):
                    title = clean(entry.findtext('title'))
                    link = (entry.findtext('link') or '').strip()
                    if not title or not link.startswith('https://') or link in seen:
                        continue
                    seen.add(link)
                    description = clean(entry.findtext('description'))
                    raw_date = entry.findtext('pubDate') or ''
                    try:
                        published = email.utils.parsedate_to_datetime(raw_date).astimezone(dt.timezone.utc)
                        date = published.isoformat()
                    except (ValueError, TypeError, IndexError):
                        date = now.isoformat()
                    source = clean(entry.findtext('source')) or 'Google News RSS'
                    items.append({'id': link, 'title': title, 'link': link,
                                  'description': description, 'date': date,
                                  'category': category, 'source': source})
                    if len(seen) >= 20:
                        break
            except Exception as exc:
                failures.append(f'{category}: {exc}')
                print('WARNING:', failures[-1])
    # Retain recently saved news for any category whose feeds failed today.
    for category in SEARCHES:
        if not any(x['category'] == category for x in items):
            items.extend(x for x in previous if x.get('category') == category)
    unique = {}
    for item in items:
        unique[(item['category'], item['id'])] = item
    items = sorted(unique.values(), key=lambda x: x['date'], reverse=True)
    per_category = {category: 0 for category in SEARCHES}
    selected = []
    for item in items:
        category = item['category']
        if per_category[category] < 20:
            selected.append(item)
            per_category[category] += 1
    if not selected:
        raise RuntimeError('No news could be fetched and no previous news exists; keeping existing file')
    payload = {'updated_at': now.isoformat(), 'items': selected, 'counts': per_category,
               'failed_sources': len(failures)}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Saved', len(selected), 'articles:', per_category)


if __name__ == '__main__':
    main()
