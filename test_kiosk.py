"""Checks the sorting of the kiosk on invented feeds, without any network.

Usage: python3 test_kiosk.py
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_kiosk as kiosk  # noqa: E402

NOW = datetime.datetime(2026, 11, 20, 12, tzinfo=datetime.timezone.utc)

FEED = """<?xml version="1.0"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>
<item><title>My first orgasm at 40 &amp; what it taught me</title>
<link>https://example.org/a</link>
<description>&lt;p&gt;A &lt;b&gt;happy&lt;/b&gt; story.&lt;/p&gt;</description>
<media:content url="https://example.org/a.jpg" width="460"/>
<pubDate>Thu, 19 Nov 2026 08:00:00 GMT</pubDate></item>
<item><title>Sex and the trial of the year</title>
<link>https://example.org/b</link>
<pubDate>Thu, 19 Nov 2026 08:00:00 GMT</pubDate></item>
<item><title>An old piece about desire</title>
<link>https://example.org/c</link>
<pubDate>Thu, 19 Nov 2020 08:00:00 GMT</pubDate></item>
<item><title>Not secure, about sex</title>
<link>http://example.org/d</link>
<pubDate>Thu, 19 Nov 2026 08:00:00 GMT</pubDate></item>
<item><title>Menopause &amp; joy &lt;script&gt;x&lt;/script&gt;</title>
<link>https://example.org/e</link>
<pubDate>Wed, 18 Nov 2026 08:00:00 GMT</pubDate></item>
<item><title>A recipe for soup</title>
<link>https://example.org/f</link>
<description>Good after sex, they say.</description>
<pubDate>Wed, 18 Nov 2026 08:00:00 GMT</pubDate></item>
<item><title>Which pill is right for you</title>
<link>https://example.org/g</link>
<pubDate>Wed, 18 Nov 2026 08:00:00 GMT</pubDate></item>
</channel></rss>"""


class KioskTest(unittest.TestCase):
    def shelves(self, default=None):
        items = kiosk.parse(FEED.encode('utf-8'))
        return kiosk.select('en', [('Example', default, items)], NOW)

    def test_reads_a_feed(self):
        first = kiosk.parse(FEED.encode('utf-8'))[0]
        self.assertEqual(first['title'],
                         'My first orgasm at 40 & what it taught me')
        self.assertEqual(first['summary'], 'A happy story.')
        self.assertEqual(first['picture'], 'https://example.org/a.jpg')

    def test_keeps_what_is_recent_light_and_on_topic(self):
        shelves = self.shelves()
        self.assertEqual([item['link'] for item in shelves['intimacy']],
                         ['https://example.org/a'])
        self.assertTrue(shelves['intimacy'][0]['testimony'])
        self.assertEqual([item['link'] for item in shelves['perimenopause']],
                         ['https://example.org/e'])
        # A trial, an old piece, an insecure address, a word in passing in
        # a summary, contraception: none of them has a place.
        self.assertEqual(set(shelves), {'intimacy', 'perimenopause'})

    def test_a_feed_on_one_topic_files_everything_under_it(self):
        links = [item['link'] for item in self.shelves('cycle')['cycle']]
        self.assertEqual(links, ['https://example.org/f'])

    def test_anything_about_sex_stays_on_its_own_page(self):
        def item(title):
            return {'title': title, 'link': 'https://example.org/x',
                    'summary': '', 'picture': None, 'date': NOW}
        # A word of another topic in the title does not move it.
        self.assertEqual(
            kiosk.topic_of('en', item('Sex on your period: nine tips'), None),
            kiosk.INTIMACY)
        self.assertEqual(
            kiosk.topic_of('en', item('Pregnancy and the best positions'),
                           kiosk.INTIMACY),
            kiosk.INTIMACY)
        self.assertEqual(
            kiosk.topic_of('fr', item("Faire l'amour pendant ses règles"),
                           None),
            kiosk.INTIMACY)
        # Sex and the young never meet, on any page.
        self.assertIsNone(
            kiosk.topic_of('en', item('What my daughter taught me'),
                           kiosk.INTIMACY))
        self.assertIsNone(
            kiosk.topic_of('fr', {**item('Grossesse : le guide'),
                                  'summary': 'Sexe et enfants.'}, None))
        # On the other pages, a child is the subject itself.
        self.assertEqual(
            kiosk.topic_of('fr', item('Grossesse : préparer son enfant'),
                           None),
            'pregnancy')
        self.assertIsNone(
            kiosk.topic_of('fr', item('Sexualité des ados : le guide'), None))
        self.assertIsNone(
            kiosk.topic_of('fr', item('Viols : la sexualité en question'),
                           kiosk.INTIMACY))
        # A loudspeaker is not a pregnancy.
        self.assertIsNone(
            kiosk.topic_of('fr', item('Les meilleures enceintes bluetooth'),
                           None))

    def test_no_more_than_a_few_items_of_one_source(self):
        items = [{
            'title': 'Sex, part %d' % index,
            'link': 'https://example.org/%d' % index,
            'summary': '',
            'picture': None,
            'date': NOW - datetime.timedelta(hours=index),
        } for index in range(10)]
        shelves = kiosk.select('en', [('Example', None, items)], NOW)
        self.assertEqual(len(shelves['intimacy']), kiosk.PER_SOURCE)
        self.assertEqual(shelves['intimacy'][0]['title'], 'Sex, part 0')

    def test_the_page_escapes_what_it_shows(self):
        text, shown = kiosk.page('en', kiosk.TOPICS, self.shelves(), NOW)
        self.assertEqual(shown, 1)
        self.assertIn('Menopause &amp; joy x', text)
        self.assertNotIn('<script', text)
        # Intimacy is on a page of its own.
        self.assertNotIn('orgasm', text)
        text, shown = kiosk.page('en', [kiosk.INTIMACY], self.shelves(), NOW)
        self.assertEqual(shown, 1)
        self.assertIn('referrerpolicy="no-referrer"', text)

    def test_an_empty_page_says_so(self):
        text, shown = kiosk.page('fr', kiosk.TOPICS, {}, NOW)
        self.assertEqual(shown, 0)
        self.assertIn('Reviens demain', text)

    def test_every_language_has_every_text(self):
        for language in kiosk.FEEDS:
            for topic in kiosk.TOPICS + [kiosk.INTIMACY]:
                self.assertIn(topic, kiosk.TEXTS[language]['topics'])
            for _, address, _, _ in kiosk.FEEDS[language]:
                self.assertTrue(address.startswith('https://'))


    def test_the_same_story_is_shown_once(self):
        first = 'Eight months pregnant, a woman finishes the marathon'
        self.assertTrue(kiosk.same_story(
            '"My last adventure": eight months pregnant, she finishes '
            'the marathon of New York', [first]))
        self.assertFalse(kiosk.same_story(
            'Pregnancy: what to pack for the hospital', [first]))

    def test_every_feed_says_its_country(self):
        # The app opens these pages by name: see lib/domain/kiosk.dart.
        self.assertEqual(kiosk.countries_of('fr'), ['be', 'ca', 'ch', 'fr'])
        self.assertEqual(kiosk.countries_of('en'), ['gb', 'us'])
        for feeds in kiosk.FEEDS.values():
            for feed in feeds:
                self.assertEqual(len(feed), 4, feed[0])
                self.assertTrue(feed[1].startswith('https://'), feed[0])


if __name__ == '__main__':
    unittest.main()
