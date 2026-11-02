"""
Canonical Source keys. See docs/adr/0001-source-key-is-web-address.md.

A Source's key is its lowercase web address: a domain without `www.`
(`bbc.co.uk`), `x.com/<handle>`, or `t.me/<channel>`.
"""

from urllib.parse import urlsplit

# Alternate address -> canonical address. Add an entry only when one Source
# really shows up under two addresses; applied to the host, then the full key.
ALIASES = {
    "twitter.com": "x.com",
    "mobile.twitter.com": "x.com",
    "bbc.com": "bbc.co.uk",
}

# Hosts where the Source is the account in the first path segment.
_ACCOUNT_HOSTS = {"x.com", "t.me"}


def source_key(url: str) -> str:
    """'https://www.BBC.com/news/1' or 'bbc.com' -> 'bbc.co.uk'; 'https://t.me/RNintel/42' -> 't.me/rnintel'."""
    url = url.strip().lower()
    parts = urlsplit(url if "://" in url else f"//{url}")
    # ponytail: unaliased subdomains (news.bbc.co.uk) count as their own Source; use tldextract (eTLD+1) if that bites
    host = (parts.hostname or "").removeprefix("www.")
    host = ALIASES.get(host, host)
    if host in _ACCOUNT_HOSTS:
        account = parts.path.strip("/").split("/")[0]
        if account:
            host = f"{host}/{account}"
    return ALIASES.get(host, host)
