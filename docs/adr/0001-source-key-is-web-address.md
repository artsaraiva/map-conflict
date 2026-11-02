# A Source's key is its web address, and the Feed is stored separately

Corroboration counts distinct Sources, so a Source's identity must not depend on the Feed that delivered the Report. A Source's key is its lowercase home address on the web: a domain without `www.` (`bbc.co.uk`), `x.com/<handle>`, or `t.me/<channel>`. The Feed is recorded in its own field on each Report. This lets RSS and GDELT agree on a Source without coordination, and stops X and Telegram accounts with the same name from colliding. When one organisation has several addresses (for example `bbc.com` and `bbc.co.uk`, or a website and an X account), a small alias map folds them onto one canonical address.

## Considered Options

- **Feed-prefixed slugs** (`tg-rnintel`, `x:handle`, `gdelt`): the previous scheme. It counts the same Source twice when it arrives through two Feeds, and collapses every Source that GDELT relays into one.
- **A full Source registry** (curated keys, names, and the addresses of every Source): rejected for now, because GDELT reaches thousands of Sources that we would never register. Addresses work for unknown Sources with no setup, and aliases are added only where an overlap actually shows up.
