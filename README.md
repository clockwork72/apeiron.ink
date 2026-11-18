# Apeiron

Source of [apeiron.ink](https://apeiron.ink). Plain static site, hosted free on
GitHub Pages. No server, no database.

## Write a post
1. Copy `posts/_example.md` to `posts/my-post.md` (the file name becomes the address: `apeiron.ink/my-post/`).
2. Edit the title, date and text. Images go in `static/images/`.
3. Run `./publish.sh "New post: my post"`.

Drafts: start the file name with `_` and it won't be published.

## How it works
`build.py` (Python, no dependencies) turns `posts/*.md` into HTML in `docs/`.
GitHub Pages serves `docs/` from branch `agent/site`. `docs/` is generated; don't edit it by hand.
