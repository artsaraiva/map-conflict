# Coding standards

Read during review. Tooling (eslint, tsc, pytest in CI) covers the mechanical rules; these are the judgement calls.

- New identifiers, docstrings, comments, and log messages use the terms in `GLOSSARY.md`. A term's _Avoid_ words appear only on lines the change left untouched.
- Code that touches Source identity follows `docs/adr/0001-source-key-is-web-address.md`; the same goes for any other ADR in `docs/adr/` covering the area changed.
