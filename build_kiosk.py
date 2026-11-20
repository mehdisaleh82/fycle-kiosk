"""Builds the kiosk: a small web site listing recent articles by topic.

Usage: python3 build_kiosk.py <output folder>

Reads the public feeds of a few media, keeps what is recent, on topic and
light in tone, and writes plain pages: no script, no cookie and no counter
of ours. Pictures are loaded from the publishers, who see the visit.
The app only hands the address of a page to the browser of the phone; it
never reads the kiosk itself (CLAUDE.md, rule 1). The sorting is automatic
and nobody reads the articles: the pages say so. Standard library only.
"""
import datetime
import email.utils
import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

AGENT = 'Mozilla/5.0 (feed reader; no personal data)'
MAX_AGE_DAYS = 45
PER_TOPIC = 12
PER_SOURCE = 4

# The pages of the kiosk. Intimacy has a page of its own, which nothing
# links to: the app opens it only for an adult who left "sex life" on.
TOPICS = ['cycle', 'perimenopause', 'pregnancy', 'fertility']
INTIMACY = 'intimacy'

# (source, feed, topic or None, country of the medium). With a topic,
# every item of the feed is filed under it unless its words say otherwise;
# without, an item needs the words of a topic to be kept.
#
# Each country has pages of its own, made of its own media only: a short
# page is an honest page, and nothing from elsewhere fills it. The pages
# of a language alone, for a country with no medium here, mix them all.
FEEDS = {
    'fr': [
        ('Le Monde', 'https://www.lemonde.fr/intimites/rss_full.xml', None, 'fr'),
        ('Libération', 'https://www.liberation.fr/arc/outboundfeeds/rss-all/category/lifestyle/intimites/?outputType=xml', None, 'fr'),
        ('La Presse', 'https://www.lapresse.ca/societe/sexualite/rss', INTIMACY, 'ca'),
        ('7sur7', 'https://www.7sur7.be/sexe-et-relations/rss.xml', INTIMACY, 'be'),
        ('Flair', 'https://www.flair.be/fr/feed/', None, 'be'),
        ('Psychologies', 'https://www.psychologies.com/rss', None, 'fr'),
        ('Marie France', 'https://www.mariefrance.fr/feed', None, 'fr'),
        ('Biba', 'https://www.bibamagazine.fr/feed', None, 'fr'),
        ('Elle Belgique', 'https://www.elle.be/fr/feed', None, 'be'),
        ('Marie Claire Belgique', 'https://www.marieclaire.be/fr/feed/', None, 'be'),
        ("Femmes d'Aujourd'hui", 'https://www.femmesdaujourdhui.be/feed/', None, 'be'),
        ('Santé Magazine', 'https://www.santemagazine.fr/feeds/rss', None, 'fr'),
        ('La Libre', 'https://www.lalibre.be/arc/outboundfeeds/rss/section/lifestyle/?outputType=xml', None, 'be'),
        ('Le Temps', 'https://www.letemps.ch/societe.rss', None, 'ch'),
        ("L'Obs", 'https://www.nouvelobs.com/rue89/rss.xml', None, 'fr'),
        ('HuffPost', 'https://www.huffingtonpost.fr/life/rss_headline.xml', None, 'fr'),
        ('Slate', 'https://www.slate.fr/rss.xml', None, 'fr'),
        ('Parents', 'https://www.parents.fr/feeds/rss', None, 'fr'),
        ('Journal des Femmes', 'https://www.journaldesfemmes.fr/rss/', None, 'fr'),
        ('Parents', 'https://www.parents.fr/feeds/rss/grossesse', 'pregnancy', 'fr'),
        ('franceinfo', 'https://www.francetvinfo.fr/sante/grossesse.rss', None, 'fr'),
        ('Santé Magazine', 'https://www.santemagazine.fr/feeds/rss/grossesse', 'pregnancy', 'fr'),
        ('Madmoizelle', 'https://www.madmoizelle.com/rubriques/daronne/grossesse/feed', 'pregnancy', 'fr'),
        ('Madmoizelle', 'https://www.madmoizelle.com/feed', None, 'fr'),
        ('Marie France', 'https://www.mariefrance.fr/tag/menopause/feed', 'perimenopause', 'fr'),
        ('Sciences et Avenir', 'https://www.sciencesetavenir.fr/sante/rss.xml', None, 'fr'),
        ('The Conversation', 'https://theconversation.com/fr/sante/articles.atom', None, 'fr'),
        ('Le Figaro', 'https://www.lefigaro.fr/rss/figaro_sante.xml', None, 'fr'),
        ('20 Minutes', 'https://www.20minutes.fr/feeds/rss-sante.xml', None, 'fr'),
        ('La Presse', 'https://www.lapresse.ca/societe/sante/rss', None, 'ca'),
        ('Aufeminin', 'https://www.aufeminin.com/rss', None, 'fr'),
        ('Moustique', 'https://www.moustique.be/feed', None, 'be'),
        ('Top Santé', 'https://www.topsante.com/rss', None, 'fr'),
        ('Paris Match Belgique', 'https://www.parismatch.be/feed/', None, 'be'),
        ('La Libre', 'https://www.lalibre.be/arc/outboundfeeds/rss/?outputType=xml', None, 'be'),
        ('DH', 'https://www.dhnet.be/arc/outboundfeeds/rss/?outputType=xml', None, 'be'),
        ('7sur7', 'https://www.7sur7.be/rss.xml', None, 'be'),
    ],
    'en': [
        ('The Guardian', 'https://www.theguardian.com/lifeandstyle/series/this-is-how-we-do-it/rss', INTIMACY, 'gb'),
        ('The Guardian', 'https://www.theguardian.com/lifeandstyle/sex/rss', INTIMACY, 'gb'),
        ('The Guardian', 'https://www.theguardian.com/society/menopause/rss', 'perimenopause', 'gb'),
        ('The Guardian', 'https://www.theguardian.com/lifeandstyle/pregnancy/rss', 'pregnancy', 'gb'),
        ('The Guardian', 'https://www.theguardian.com/society/menstruation/rss', 'cycle', 'gb'),
        ('The Guardian', 'https://www.theguardian.com/society/fertility-problems/rss', 'fertility', 'gb'),
        ('Cosmopolitan', 'https://www.cosmopolitan.com/rss/sex-love.xml/', INTIMACY, 'us'),
        ('Cosmopolitan', 'https://www.cosmopolitan.com/uk/rss/love-sex.xml/', INTIMACY, 'gb'),
        ('Metro', 'https://metro.co.uk/lifestyle/sex/feed/', INTIMACY, 'gb'),
        ('Self', 'https://www.self.com/feed/rss', None, 'us'),
        ('Bustle', 'https://www.bustle.com/rss', None, 'us'),
        ('Red', 'https://www.redonline.co.uk/rss/all.xml/', None, 'gb'),
        ('Good Housekeeping', 'https://www.goodhousekeeping.com/uk/rss/health.xml/', None, 'gb'),
        ('The Guardian', 'https://www.theguardian.com/lifeandstyle/parents-and-parenting/rss', None, 'gb'),
        ("Women's Health", 'https://www.womenshealthmag.com/uk/rss/all.xml/', None, 'gb'),
        ('Stylist', 'https://www.stylist.co.uk/feed', None, 'gb'),
        ('Metro', 'https://metro.co.uk/lifestyle/health/feed/', None, 'gb'),
        ('Cosmopolitan', 'https://www.cosmopolitan.com/uk/rss/body.xml/', None, 'gb'),
        ('Scary Mommy', 'https://www.scarymommy.com/rss', None, 'us'),
        ('Oprah Daily', 'https://www.oprahdaily.com/rss/all.xml/', None, 'us'),
        ("Women's Health", 'https://www.womenshealthmag.com/rss/all.xml/', None, 'us'),
        ('Romper', 'https://www.romper.com/rss', None, 'us'),
    ],
}

# Words that file an item under a topic. Intimacy, last here, is checked
# first (see topic_of); the others in this order.
WORDS = {
    'fr': [
        ('perimenopause', r'ménopaus|bouffées? de chaleur'),
        ('fertility', r'fertilité|\bpma\b|\bfiv\b|tomber enceinte|désir d.enfant|projet bébé|essai bébé|ovocyte|avoir un (enfant|bébé)'),
        ('pregnancy', r'grossesse|enceinte(?!s? (bluetooth|connectée|sans fil|nomade))|accouch|post-partum|postpartum|allaitement|jeune maman|jeunes? mères?|nouveau-né|nourrisson|sage-femme|maternité|congé (de )?(maternité|paternité)'),
        ('cycle', r'\b(ses|mes|tes|des|les|premières|pendant les|avoir ses) règles\b(?! (de|du|d.|pour|sur|à)\b)|menstru|cycle féminin|syndrome prémenstruel|\bspm\b|ovulation|protections? (périodiques?|hygiéniques?)|\btampons?\b(?! (encreur|de|du)\b)'),
        (INTIMACY, r'\bsexe\b|\bsexo\b|sexualité|sexuel|orgasme|\bdésir\b|libido|plaisir féminin|clitoris|masturb|sextoy|sex-toy|faire l.amour|\bjouir\b|jouissance|fantasme|au lit\b|érotique|charnel|coquin'),
    ],
    'en': [
        ('perimenopause', r'menopaus|hot flush|hot flash'),
        ('fertility', r'fertility|\bivf\b|trying to conceive|egg freezing|frozen eggs|trying for a baby'),
        ('pregnancy', r'pregnan|childbirth|giving birth|postpartum|postnatal|breastfeed|new mum|new mom|newborn|midwi|maternity'),
        ('cycle', r'\b(your|my|her|their|on your|first) periods?\b|menstru|\bpms\b|ovulation|tampons?\b'),
        (INTIMACY, r'\bsex\b|sexual|orgasm|\bdesire\b|libido|clitoris|masturbat|sex toy|vibrator|in bed\b|foreplay|\bkink|erotic|intimacy'),
    ],
}

# The kiosk is for the light side of things. An item with one of these
# words is left out, whatever the rest says. Contraception is left out as
# well: the app gives no advice on it (CLAUDE.md, rule 7).
NOT_LIGHT = {
    'fr': r'viols?\b|violé|violeur|agress|violen|féminicide|meurtr|\btué|\bmorts?\b|\bmortes?\b|\bmourir|\bmeurt|décès|décéd|suicid|cancer|tumeur|procès|tribunal|condamn|plainte|accusé|inceste|pédo|harcèlement|\bdeuil|fausses? couches?|drame|tragédie|guerre|attentat|maladie grave|\bist\b|\bvih\b|sida|infection|scandale|prison|police|proxén|prostitu|\bporno|contracepti|pilule|stérilet|\bivg\b|avortement|appli de suivi|application de suivi|travailleu|risque|danger|alerte|inqui[eé]t|interdi|pesticide|toxique|\bcrise|pénurie|carence|parkinson|endométriose|douleur|souffr|\bpeur|honte|tabou|précarité|arnaque|rupture|divorce|tromp|infid|déteste|mal-être|déconseill|misogyn|sexis|\d ?€|\beuros?\b|bon plan|\bpromo',
    'en': r'\brape|rapist|assault|abus|violen|murder|\bkill|\bdead\b|\bdeath|\bdied\b|\bdies\b|\bdying\b|suicid|cancer|tumou?r|\btrial\b|court\b|convict|sentenc|lawsuit|accus|incest|\bpaedo|\bpedo|groom|harass|grief|griev|miscarriage|stillb|tragedy|\bwar\b|attack|\bsti\b|\bstis\b|\bhiv\b|infection|scandal|prison|police|traffick|\bporn|contracepti|\bpills?\b|\biud\b|abortion|period.track|tracking app|\bshop\b|\bdeals?\b|\bbest \d+|black friday|\bsale\b|\bbanned|shocking|denial|closure|crisis|\brisk|\bwarn|\bfear|toxic|chemical|(?<!in-)\blaws?\b|\bban\b|despair|problematic|epidemic|\bcope\b|endometriosis|\bpain|suffer|shame|poverty|scam|divorce|cheat|affair|brief letters|– review|podcast|sex work(?!s\b)|onlyfans|life-threatening|bleed|\bhurt|teen pregnan|\d+ best\b|best products|\breview\b|tested',
}

# Words about minors. An item that has them is never filed under intimacy,
# and is left out altogether if anything in it speaks of sex. On the other
# pages, a baby or a child is the subject itself.
MINORS = {
    'fr': r'mineur|\bados?\b|adolescen|collégien|lycéen|\benfants?\b|\bbébés?\b|\bfilles?\b|\bfils\b|\bélèves?\b',
    'en': r'\bteen|\bchild|\bkids?\b|\bbab(y|ies)\b|schoolgirl|underage|\bminors?\b|\bdaughters?\b|\bsons?\b|\bpupils?\b',
}

# Someone speaking for herself.
TESTIMONY = {
    'fr': r'témoign|\braconte|\bconfie|\bj.ai\b|\bje\b|\bmoi,|\bmon\b|\bma\b',
    'en': r'\bi\b|\bmy\b|\bme\b|this is how we do it|confession|her story|their story',
}

TEXTS = {
    'fr': {
        'title': 'Le kiosque',
        'date': '%d/%m/%Y',
        'day': '%d/%m',
        'lead': "Des articles récents, choisis chaque jour dans la presse.",
        'updated': 'Mis à jour le %s',
        'testimony': 'Témoignage',
        'empty': "Rien de neuf aujourd'hui. Reviens demain.",
        'note': "Sélection automatique : personne n'a relu ces articles. Les titres et les images appartiennent à leurs éditeurs. Rien ici n'est un avis médical. Les images sont servies par les sites des journaux, qui voient donc ta visite dès l'ouverture de cette page, comme en ouvrant un article.",
        'topics': {
            'cycle': 'Cycle et règles',
            'perimenopause': 'Périménopause',
            'pregnancy': 'Grossesse et bébé',
            'fertility': 'Fertilité',
            INTIMACY: 'Intimité',
        },
    },
    'en': {
        'title': 'The newsstand',
        'date': '%Y-%m-%d',
        'day': '%m-%d',
        'lead': 'Recent articles, picked from the press every day.',
        'updated': 'Updated on %s',
        'testimony': 'First person',
        'empty': 'Nothing new today. Come back tomorrow.',
        'note': 'Picked automatically: nobody has read these articles. Titles and pictures belong to their publishers. Nothing here is medical advice. Pictures are served by the sites of the publishers, which therefore see your visit as soon as this page opens, as they do when you open an article.',
        'topics': {
            'cycle': 'Cycle and periods',
            'perimenopause': 'Perimenopause',
            'pregnancy': 'Pregnancy and baby',
            'fertility': 'Fertility',
            INTIMACY: 'Intimacy',
        },
    },
}



def countries_of(language):
    """The countries with pages of their own in a language."""
    return sorted({feed[3] for feed in FEEDS[language]})


MEDIA = '{http://search.yahoo.com/mrss/}'
ATOM = '{http://www.w3.org/2005/Atom}'
TAG = re.compile(r'<[^>]+>')
IMAGE = re.compile(r'<img[^>]+src=["\'](https://[^"\']+)["\']', re.I)


def plain(text):
    """The text of a feed field, without markup."""
    return ' '.join(html.unescape(TAG.sub(' ', text or '')).split())


def secure(address):
    address = (address or '').strip()
    if address.startswith('https://') and not re.search(r'[\s"<>]', address):
        return address
    return None


def picture_of(item, raw_description):
    best, width = None, -1
    for node in item.iter():
        if node.tag in (MEDIA + 'content', MEDIA + 'thumbnail', 'enclosure'):
            kind = node.get('type', '') or node.get('medium', '')
            if node.tag == 'enclosure' and not kind.startswith('image'):
                continue
            address = secure(node.get('url'))
            try:
                size = int(node.get('width') or 0)
            except ValueError:
                size = 0
            # Wide enough for a phone, no wider than needed.
            score = size if size <= 800 else 0
            if address and score > width:
                best, width = address, score
    if best:
        return best
    found = IMAGE.search(raw_description or '')
    return secure(html.unescape(found.group(1))) if found else None


def date_of(text):
    text = (text or '').strip()
    if not text:
        return None
    try:
        when = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            when = datetime.datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return when


def parse(data):
    """The items of a feed: title, link, summary, picture, date."""
    root = ET.fromstring(data)
    found = []
    for item in root.iter('item'):
        raw = item.findtext('description') or ''
        found.append({
            'title': plain(item.findtext('title')),
            'link': secure(item.findtext('link')),
            'summary': plain(raw),
            'picture': picture_of(item, raw),
            'date': date_of(item.findtext('pubDate')),
        })
    for entry in root.iter(ATOM + 'entry'):
        link = None
        for node in entry.findall(ATOM + 'link'):
            if node.get('rel', 'alternate') == 'alternate':
                link = node.get('href')
        raw = entry.findtext(ATOM + 'summary') or ''
        found.append({
            'title': plain(entry.findtext(ATOM + 'title')),
            'link': secure(link),
            'summary': plain(raw),
            'picture': picture_of(entry, raw),
            'date': date_of(entry.findtext(ATOM + 'updated')),
        })
    return found


def topic_of(language, item, default):
    """Where an item goes, or None when it has no place in the kiosk."""
    text = ('%s %s' % (item['title'], item['summary'])).lower()
    if re.search(NOT_LIGHT[language], text):
        return None
    title = item['title'].lower()
    intimacy = WORDS[language][-1][1]
    about_minors = re.search(MINORS[language], text) is not None
    # Sex and minors never meet, on any page.
    if about_minors and (default == INTIMACY or re.search(intimacy, text)):
        return None
    # Anything about sex goes to the page about intimacy and nowhere else:
    # the general page is open to all, minors included.
    if default == INTIMACY:
        return INTIMACY
    for topic, words in [WORDS[language][-1]] + WORDS[language][:-1]:
        if re.search(words, title):
            return topic
    # A feed about everything is judged on its titles alone: a word in
    # passing in a summary says little about the subject.
    return default


def is_testimony(language, item):
    return re.search(TESTIMONY[language], item['title'].lower()) is not None


def words_of(title):
    return {word for word in re.findall(r'\w{4,}', title.lower())}


def same_story(title, others):
    """Whether a title tells what one of the others already tells: the
    same dispatch is often printed by several papers."""
    words = words_of(title)
    for other in others:
        theirs = words_of(other)
        if words and theirs and (
                len(words & theirs) >= 0.5 * min(len(words), len(theirs))):
            return True
    return False


def select(language, feeds, now):
    """Sorts the items of the feeds: {topic: [item, ...]}, newest first."""
    limit = now - datetime.timedelta(days=MAX_AGE_DAYS)
    shelves, seen = {}, set()
    for source, default, items in feeds:
        for item in items:
            if not item['title'] or not item['link'] or item['link'] in seen:
                continue
            if item['date'] is None or item['date'] < limit:
                continue
            topic = topic_of(language, item, default)
            if topic is None:
                continue
            seen.add(item['link'])
            shelves.setdefault(topic, []).append(dict(
                item, source=source, testimony=is_testimony(language, item)))
    for topic, items in shelves.items():
        items.sort(key=lambda item: item['date'], reverse=True)
        kept, count = [], {}
        for item in items:
            count[item['source']] = count.get(item['source'], 0) + 1
            if count[item['source']] > PER_SOURCE:
                continue
            if same_story(item['title'], [one['title'] for one in kept]):
                continue
            kept.append(item)
        shelves[topic] = kept[:PER_TOPIC]
    return shelves


STYLE = """
:root{color-scheme:light dark;--bg:#fbf7f8;--card:#fff;--ink:#2b2126;
--soft:#75656d;--accent:#b0456b;--line:#eadfe3}
@media (prefers-color-scheme:dark){:root{--bg:#191316;--card:#241c20;
--ink:#f3e9ed;--soft:#b3a2aa;--accent:#f09ab8;--line:#35292f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:720px;margin:0 auto;padding:20px 16px 40px}
h1{font-size:1.7rem;margin:0 0 4px}
h2{font-size:1.2rem;margin:32px 0 12px}
p.lead,p.note,p.date,p.empty{color:var(--soft);margin:0}
p.date{font-size:.85rem;margin-top:4px}
p.note{font-size:.8rem;margin-top:36px;padding-top:16px;
border-top:1px solid var(--line)}
ul{list-style:none;margin:0;padding:0;display:grid;gap:12px;
grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}
li a{display:block;height:100%;background:var(--card);color:inherit;
text-decoration:none;border:1px solid var(--line);border-radius:16px;
overflow:hidden}
li img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;
background:var(--line)}
li div{padding:12px}
li span{display:block;font-size:.78rem;color:var(--soft)}
li b{display:inline-block;font-size:.72rem;font-weight:600;
color:var(--accent);border:1px solid var(--accent);border-radius:99px;
padding:1px 8px;margin-bottom:6px}
li strong{display:block;font-weight:600;margin-top:2px}
"""


def page(language, topics, shelves, now):
    texts = TEXTS[language]
    out = [
        '<!doctype html>',
        '<html lang="%s" dir="auto">' % language,
        '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta name="robots" content="noindex,nofollow">',
        '<meta name="referrer" content="no-referrer">',
        '<title>%s</title>' % html.escape(texts['title']),
        '<style>%s</style>' % STYLE,
        '</head>',
        '<body><main>',
        '<h1>%s</h1>' % html.escape(texts['title']),
        '<p class="lead">%s</p>' % html.escape(texts['lead']),
        '<p class="date">%s</p>' % html.escape(
            texts['updated'] % now.strftime(texts['date'])),
    ]
    shown = 0
    for topic in topics:
        items = shelves.get(topic, [])
        if not items:
            continue
        shown += len(items)
        out.append('<h2>%s</h2>' % html.escape(texts['topics'][topic]))
        out.append('<ul>')
        for item in items:
            out.append('<li><a href="%s" rel="noopener noreferrer">' %
                       html.escape(item['link'], quote=True))
            if item['picture']:
                out.append(
                    '<img src="%s" alt="" loading="lazy" '
                    'referrerpolicy="no-referrer">' %
                    html.escape(item['picture'], quote=True))
            out.append('<div>')
            if item['testimony']:
                out.append('<b>%s</b>' % html.escape(texts['testimony']))
            out.append('<span>%s · %s</span>' % (
                html.escape(item['source']),
                item['date'].strftime(texts['day'])))
            out.append('<strong>%s</strong>' % html.escape(item['title']))
            out.append('</div></a></li>')
        out.append('</ul>')
    if shown == 0:
        out.append('<p class="empty">%s</p>' % html.escape(texts['empty']))
    out.append('<p class="note">%s</p>' % html.escape(texts['note']))
    out.append('</main></body></html>')
    return '\n'.join(out) + '\n', shown


def fetch(address):
    request = urllib.request.Request(address, headers={'User-Agent': AGENT})
    with urllib.request.urlopen(request, timeout=30) as answer:
        return answer.read()


def main(folder):
    now = datetime.datetime.now(datetime.timezone.utc)
    total = 0
    for language, feeds in FEEDS.items():
        read = []
        for source, address, default, country in feeds:
            try:
                items = parse(fetch(address))
                print('%3d  %s' % (len(items), address))
                read.append((source, default, items, country))
            except Exception as error:  # noqa: BLE001 - a feed that fails
                print('--   %s  (%s)' % (address, type(error).__name__))
        # The language alone, then each country with its own media only.
        for country in [None] + countries_of(language):
            shelves = select(language, [
                feed[:3] for feed in read
                if country is None or feed[3] == country], now)
            parts = [folder, language] + ([country] if country else [])
            os.makedirs(os.path.join(*parts), exist_ok=True)
            for name, topics in (('index', TOPICS), (INTIMACY, [INTIMACY])):
                text, shown = page(language, topics, shelves, now)
                if country is None:
                    total += shown
                path = os.path.join(*(parts + [name + '.html']))
                with open(path, 'w', encoding='utf-8',
                          newline='\n') as file:
                    file.write(text)
                print('%s: %d articles' % (path, shown))
    # The root says nothing: the app always opens a page of a language.
    with open(os.path.join(folder, 'index.html'), 'w', encoding='utf-8',
              newline='\n') as file:
        file.write('<!doctype html><meta charset="utf-8">'
                   '<meta name="robots" content="noindex,nofollow">'
                   '<title>Fycle</title>\n')
    # Every feed failing at once is a breakdown, not a quiet day.
    return 0 if total > 0 else 1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
