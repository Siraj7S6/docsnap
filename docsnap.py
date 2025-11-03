#!/usr/bin/env python3
"""
DocSnap.py
----------------------
Fetches documentation pages from a docs site (default: https://docs.flutter.dev),
organizes them into a book-like HTML with a title page and index (TOC), then converts to PDF.

USAGE:
    python3 docsnap.py --start-url https://docs.flutter.dev --output flutter_docs.pdf

DEPENDENCIES (install with pip):
    pip install requests beautifulsoup4 markdownify markdown weasyprint tqdm

NOTES:
  - WeasyPrint requires some system libraries (cairo, Pango, GDK-PixBuf). On Debian/Ubuntu:
        sudo apt-get install libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev libssl-dev libcairo2
    - On macOS, install Cairo and Pango via Homebrew.
  - This script respects robots.txt and will only crawl allowed paths.
  - The script tries to extract the main content from each page (main/article/div[role=main]).
  - For large sites, crawling may take long; you can provide a list of specific URLs instead.
"""

import argparse
import os
import re
import sys
import time
import urllib.parse as urlparse
from collections import OrderedDict

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from markdown import markdown as md_to_html
from weasyprint import HTML, CSS
from tqdm import tqdm
from urllib.robotparser import RobotFileParser

# -------------------- Helper utilities --------------------

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "doc-builder/1.0 (+https://example.com)"
})

def is_same_domain(start_netloc, link):
    try:
        p = urlparse.urlparse(link)
        if not p.netloc:
            return True
        return p.netloc == start_netloc
    except Exception:
        return False

def normalize_link(base, href):
    if not href:
        return None
    href = href.split('#')[0]  # drop fragment
    href = href.strip()
    if href.startswith('mailto:') or href.startswith('tel:'):
        return None
    return urlparse.urljoin(base, href)

def allowed_by_robots(start_url, url):
    try:
        parsed = urlparse.urlparse(start_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(SESSION.headers['User-Agent'], url)
    except Exception:
        return True  # be permissive if robots parsing fails

def extract_main_html(soup):
    # Try several fallbacks to locate the main content
    selectors = [
        ("main", None),
        ("article", None),
        ("div[role=main]", None),
        ("div[class*='content']", None),
        ("div[class*='main-content']", None),
        ("div[id*='content']", None),
    ]
    for sel, _ in selectors:
        try:
            tag = soup.select_one(sel)
        except Exception:
            tag = None
        if tag and tag.get_text(strip=True):
            return tag
    # Fallback: body
    return soup.body or soup

def clean_html_fragment(fragment):
    # Remove scripts, styles, navs, forms
    for tag in fragment.select("script, style, nav, form, footer, header, noscript"):
        tag.decompose()
    # Remove common junk by classes or ids
    for cls in ["edit-on-github", "sidebar", "toc", "breadcrumbs", "page-nav", "nav", "site-footer", "site-header"]:
        for t in fragment.select(f".{cls}"):
            t.decompose()
    # Remove comments
    for comment in fragment.find_all(string=lambda text: isinstance(text, type(fragment.original_encoding))):
        pass
    return fragment

# -------------------- Crawler and assembler --------------------

def crawl_docs(start_url, max_pages=300, delay=0.5, allowed_path_prefix=None):
    """
    Crawl internal pages starting from start_url.
    Returns OrderedDict of URL -> (title, html_content)
    """
    parsed = urlparse.urlparse(start_url)
    base_netloc = parsed.netloc
    scheme_and_netloc = f"{parsed.scheme}://{parsed.netloc}"
    to_visit = [start_url]
    visited = set()
    pages = OrderedDict()

    pbar = tqdm(total=max_pages, desc="Crawling pages", unit="page")
    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        if not is_same_domain(base_netloc, url):
            visited.add(url)
            continue
        if allowed_path_prefix and not url.startswith(allowed_path_prefix):
            visited.add(url)
            continue
 #       if not allowed_by_robots(start_url, url):
  #          print(f"[robots.txt] Skipping {url}")
   #         visited.add(url)
    #        continue
        try:
            resp = SESSION.get(url, timeout=20)
            if resp.status_code != 200:
                visited.add(url)
                continue
        except Exception as e:
            print("Request failed:", e)
            visited.add(url)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url
        main = extract_main_html(soup)
        if main is None:
            visited.add(url)
            continue
        main = clean_html_fragment(main)
        pages[url] = (title, str(main))

        visited.add(url)
        pbar.update(1)

        # Find internal links
        for a in soup.find_all("a", href=True):
            href = normalize_link(url, a['href'])
            if not href: continue
            # keep only docs pages in same domain
            if not is_same_domain(base_netloc, href):
                continue
            # optionally filter out file types
            if re.search(r'\.(jpg|jpeg|png|gif|svg|pdf|zip|tar|gz|mp4|webm)$', href, re.I):
                continue
            if href not in visited and href not in to_visit and href.startswith(scheme_and_netloc):
                to_visit.append(href)
        time.sleep(delay)
    pbar.close()
    return pages

def build_book_html(pages, book_title="Documentation Book", author=None):
    """
    Build a single HTML string that contains:
      - Title page
      - Table of Contents (with links)
      - Chapters (each page content)
    """
    # Generate TOC entries from headings in each page
    toc_entries = []
    chapters_html = []
    for i, (url, (title, html_content)) in enumerate(pages.items(), start=1):
        soup = BeautifulSoup(html_content, "html.parser")
        # Ensure headings have ids
        for h in soup.find_all(re.compile("^h[1-6]$")):
            if not h.get('id'):
                safe_id = re.sub(r'[^a-zA-Z0-9_-]+', '-', h.get_text())[:60]
                h['id'] = f"p{i}-{safe_id}"
        # Chapter heading
        chapter_title = soup.find(re.compile("^h[1-3]$"))
        chapter_title_text = chapter_title.get_text(strip=True) if chapter_title else title
        chapter_id = f"chapter-{i}"
        toc_entries.append((chapter_title_text, chapter_id))
        # Wrap content
        chapter_html = f'<section class="chapter" id="{chapter_id}">\n<h1>{chapter_title_text}</h1>\n<div class="source-url">Source: <a href="{url}">{url}</a></div>\n{str(soup)}</section>\n<div style="page-break-after: always;"></div>'
        chapters_html.append(chapter_html)

    # Simple CSS for printing
    css = """
    body { font-family: "DejaVu Sans", "Arial", sans-serif; margin: 2cm; font-size: 12pt; color: #222; }
    h1 { font-size: 20pt; margin-top: 0.5em; margin-bottom: 0.3em; }
    h2 { font-size: 16pt; margin-top: 0.6em; }
    .title-page { text-align: center; margin-top: 6cm; }
    .title-page h1 { font-size: 36pt; margin-bottom: 0.2em; }
    .toc { margin-top: 2cm; }
    .toc ul { list-style: none; padding-left: 0; }
    .toc a { text-decoration: none; color: #1a0dab; }
    .chapter { margin-top: 1em; }
    .source-url { font-size: 9pt; color: #555; margin-bottom: 0.5em; }
    pre { white-space: pre-wrap; word-wrap: break-word; background: #f7f7f7; padding: 0.5em; border-radius: 4px; }
    code { font-family: monospace; }
    .idx { font-size: 11pt; }
    """

    # Build HTML
    title_html = f"<div class='title-page'><h1>{book_title}</h1>"
    if author:
        title_html += f"<div class='author'>By {author}</div>"
    title_html += f"<div class='meta'>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</div></div><div style='page-break-after: always;'></div>"

    toc_html = "<div class='toc'><h2>Index / Table of Contents</h2><ul>"
    for t, cid in toc_entries:
        toc_html += f'<li><a href="#{cid}">{t}</a></li>\n'
    toc_html += "</ul></div><div style='page-break-after: always;'></div>"

    body_html = "\n".join(chapters_html)

    full_html = f"<!doctype html><html><head><meta charset='utf-8'><title>{book_title}</title><style>{css}</style></head><body>{title_html}{toc_html}{body_html}</body></html>"
    return full_html

def save_html_to_pdf(html_str, output_path, base_url=None):
    """
    Convert HTML string to PDF using WeasyPrint.
    """
    HTML(string=html_str, base_url=base_url).write_pdf(output_path, stylesheets=[CSS(string='@page { size: A4; margin: 2cm }')])

# -------------------- Commandline interface --------------------

def main():
    parser = argparse.ArgumentParser(description="Build an organized PDF book from documentation site.")
    parser.add_argument("--start-url", "-s", required=False, default="https://docs.flutter.dev", help="Starting URL for the documentation (default: https://docs.flutter.dev)")
    parser.add_argument("--output", "-o", required=False, default="documentation_book.pdf", help="Output PDF filename (default: documentation_book.pdf)")
    parser.add_argument("--max-pages", type=int, default=200, help="Maximum number of pages to crawl (default: 200)")
    parser.add_argument("--delay", type=float, default=0.4, help="Delay between requests in seconds (default: 0.4)")
    parser.add_argument("--no-crawl", action="store_true", help="If set, do not crawl; instead expect --urls-file with list of pages to include")
    parser.add_argument("--urls-file", help="A file containing newline-separated URLs to include (used with --no-crawl)")
    parser.add_argument("--book-title", default="Documentation Book", help="Title to put on the PDF book")
    parser.add_argument("--author", default=None, help="Author/creator name for the title page")
    parser.add_argument("--allowed-prefix", default=None, help="Only include URLs that start with this prefix (useful to limit to /docs/)")
    args = parser.parse_args()

    if args.no_crawl:
        if not args.urls_file:
            print("When --no-crawl is used you must provide --urls-file with URLs to include.")
            sys.exit(1)
        with open(args.urls_file, "r", encoding="utf-8") as f:
            urls = [u.strip() for u in f if u.strip()]
        pages = OrderedDict()
        for u in urls:
            print("Fetching", u)
            try:
                resp = SESSION.get(u, timeout=20)
                if resp.status_code != 200:
                    print("Skipped:", u, "status", resp.status_code)
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else u
                main = extract_main_html(soup)
                main = clean_html_fragment(main)
                pages[u] = (title, str(main))
                time.sleep(args.delay)
            except Exception as e:
                print("Error fetching", u, e)
    else:
        pages = crawl_docs(args.start_url, max_pages=args.max_pages, delay=args.delay, allowed_path_prefix=args.allowed_prefix)

    if not pages:
        print("No pages collected. Exiting.")
        sys.exit(1)

    print(f"Building book HTML with {len(pages)} pages...")
    html_str = build_book_html(pages, book_title=args.book_title, author=args.author)
    out = os.path.abspath(args.output)
    print("Converting to PDF (this may take a while)...")
    save_html_to_pdf(html_str, out, base_url=args.start_url)
    print("Done. PDF saved to:", out)

if __name__ == "__main__":
    main()
