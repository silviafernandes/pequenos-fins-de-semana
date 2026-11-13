"""Public PlayLab entry points; general age ranges never become session evidence."""
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

AGENDA='https://sites.google.com/view/playlabporto/agenda'
WEEKEND_SHORT='https://forms.gle/hMDB9KzHpHbUbagV8'
WEEKEND_FORM='https://docs.google.com/forms/d/e/1FAIpQLScd4N4mxUFYqP6l6kMYB6LvdyTCm4_Q5LGWyfWp5ekNYFtKSw/viewform'


def programme_links(html, url):
    """Follow monthly issues even when their titles contain no baby keywords."""
    parsed=urlparse(url)
    if parsed.hostname!='playlabporto.beehiiv.com':return []
    found=[]
    for a in BeautifulSoup(html,'html.parser').find_all('a',href=True):
        target=urljoin(url,a['href'])
        p=urlparse(target)
        if p.scheme=='https' and p.hostname=='playlabporto.beehiiv.com' and p.path.startswith('/p/'):
            found.append((target,a.get_text(' ',strip=True) or 'Programa PlayLab'))
    return list(dict(found).items())


def weekend_form(html, url):
    """Use the observed expanded URL only while the agenda still links to it."""
    if url.rstrip('/')!=AGENDA:return None
    for a in BeautifulSoup(html,'html.parser').find_all('a',href=True):
        target=urljoin(url,a['href'])
        # Google Sites wraps outgoing public links in a Google redirect.
        if urlparse(target).hostname=='www.google.com' and urlparse(target).path=='/url':
            from urllib.parse import parse_qs
            target=parse_qs(urlparse(target).query).get('q',[''])[0]
        if target.rstrip('/')==WEEKEND_SHORT:return WEEKEND_FORM
    return None
