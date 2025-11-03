# 📘 DocSnap

**DocSnap** converts online documentation and Word (.docx) files into a clean, organized PDF book with a title page and index for easy offline reading.

### 🚀 Features

* Converts websites or Word documents into PDFs
* Creates title page, table of contents, and chapters
* Supports custom titles, authors, and page limits
* Respects website robots.txt rules
* Works on Windows, macOS, and Linux

### 🧩 Installation

Requires Python 3.10 or newer.
Install dependencies:

```bash
pip install requests beautifulsoup4 markdownify markdown weasyprint tqdm python-docx
```

Windows users must also install the GTK3 runtime from
[GTK for Windows Runtime Environment Installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases).

### ⚙️ Usage

Convert documentation:

```bash
python docsnap.py --start-url https://docs.flutter.dev --output flutter.pdf --max-pages 20
```

Convert a Word file:

```bash
python docsnap.py --doc-file myfile.docx --output myfile.pdf
```

### 🧠 Notes

If modules are missing, reinstall with:

```bash
python -m pip install requests
```

Developed by **Mir Talpur** — 2025.
DocSnap: your instant documentation-to-book creator.
