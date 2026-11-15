#!/usr/bin/env python3
"""Collect German RSS news for the static Deutsch Lernen reading app."""
import datetime as dt
import email.utils
import html
import json
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

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
# Independent publisher feeds. Individual feed URLs may change over time.
FEEDS = {
    'Politik': ['https://www.tagesschau.de/inland/index~rss2.xml', 'https://www.tagesschau.de/xml/rss2/'],
    'Wirtschaft': ['https://www.tagesschau.de/wirtschaft/index~rss2.xml', 'https://www.deutschlandfunk.de/wirtschaft-106.rss'],
    'Technologie': ['https://www.heise.de/rss/heise-atom.xml', 'https://www.tagesschau.de/wissen/technologie/index~rss2.xml'],
    'Wissenschaft': ['https://www.tagesschau.de/wissen/index~rss2.xml', 'https://www.deutschlandfunk.de/wissenschaft-100.rss'],
    'Gesundheit': ['https://www.tagesschau.de/wissen/gesundheit/index~rss2.xml', 'https://www.deutschlandfunk.de/gesundheit-100.rss'],
    'International': ['https://www.tagesschau.de/ausland/index~rss2.xml', 'https://www.deutschlandfunk.de/nachrichten-100.rss'],
}
NS = {'atom': 'http://www.w3.org/2005/Atom'}

def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', value or ''))).strip()

def download(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; DeutschLernen/1.0; educational RSS reader)',
        'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
    })
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read()

def parse_date(raw, fallback):
    if not raw:
        return fallback
    try:
        date = email.utils.parsedate_to_datetime(raw)
    except (ValueError, TypeError, IndexError):
        try:
            date = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except ValueError:
            return fallback
    if date.tzinfo is None:
        date = date.replace(tzinfo=dt.timezone.utc)
    return date.astimezone(dt.timezone.utc).isoformat()

def parse_feed(xml_bytes, category, fallback_source, now):
    root = ET.fromstring(xml_bytes)
    found = []
    entries = root.findall('.//item')
    if not entries:
        entries = root.findall('.//atom:entry', NS)
    for entry in entries[:40]:
        atom = entry.tag.endswith('entry')
        if atom:
            title = clean(entry.findtext('atom:title', default='', namespaces=NS))
            link_node = entry.find('atom:link', NS)
            link = link_node.get('href', '') if link_node is not None else ''
            description = clean(entry.findtext('atom:summary', default='', namespaces=NS)
                                or entry.findtext('atom:content', default='', namespaces=NS))
            raw_date = entry.findtext('atom:published', default='', namespaces=NS) or entry.findtext('atom:updated', default='', namespaces=NS)
            source = fallback_source
        else:
            title = clean(entry.findtext('title'))
            link = (entry.findtext('link') or '').strip()
            description = clean(entry.findtext('description'))
            raw_date = entry.findtext('pubDate') or ''
            source = clean(entry.findtext('source')) or fallback_source
        if not title or not link.startswith(('https://', 'http://')):
            continue
        found.append({'id': link, 'title': title, 'link': link, 'description': description,
                      'date': parse_date(raw_date, now), 'category': category, 'source': source})
    return found

def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    prior = {}
    if OUT.exists():
        try:
            prior = json.loads(OUT.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            pass
    previous = prior.get('items', []) if isinstance(prior.get('items'), list) else []
    items, failures = [], []
    for category, sources in FEEDS.items():
        category_items = []
        # Publisher feeds first, Google News searches as an additional fallback.
        urls = list(sources)
        urls += ['https://news.google.com/rss/search?' + urllib.parse.urlencode({
            'q': q + ' when:7d', 'hl': 'de', 'gl': 'DE', 'ceid': 'DE:de'}) for q in SEARCHES[category]]
        for url in urls:
            try:
                retrieved = parse_feed(download(url), category, urllib.parse.urlparse(url).hostname or 'RSS', now)
                category_items.extend(retrieved)
                print(f'OK: {category}: {len(retrieved)} items from {urllib.parse.urlparse(url).hostname}')
                if len(category_items) >= 25:
                    break
            except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError, ValueError) as exc:
                failures.append(f'{category}: {url}: {exc}')
                print('WARNING:', failures[-1])
        if not category_items:
            category_items = [x for x in previous if x.get('category') == category]
            if category_items:
                print(f'FALLBACK: {category}: retaining {len(category_items)} previous items')
        items.extend(category_items)
    unique = {}
    for item in items:
        category = item.get('category')
        link = item.get('link')
        if category in SEARCHES and isinstance(link, str) and link:
            unique[(category, link)] = item
    sorted_items = sorted(unique.values(), key=lambda x: x.get('date', ''), reverse=True)
    counts = {category: 0 for category in SEARCHES}
    selected = []
    for item in sorted_items:
        category = item['category']
        if counts[category] < 20:
            selected.append(item)
            counts[category] += 1
    if not selected:
        raise RuntimeError('No news available from any source and no previous news.json exists. Try rerunning later.')
    payload = {'updated_at': now, 'items': selected, 'counts': counts, 'failed_sources': len(failures)}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Saved', len(selected), 'articles:', counts)
    for category, count in counts.items():
        if count == 0:
            print('WARNING: No articles available for', category)

if __name__ == '__main__':
    main()
