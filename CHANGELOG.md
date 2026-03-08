# Changelog

## [Unreleased] - 2026-03-08

### Changed
- centralisation du chargement de configuration et des variables d’environnement
- refactor de `main.py` avec point d’entrée explicite et moins d’effets de bord
- utilisation de clés de sources stables pour éviter la logique basée sur les titres distants
- amélioration du fallback de résumé, surtout pour Reddit quand la description est vide
- ajout de timeouts HTTP et validation des URLs injectées dans les messages Telegram
- correction du nettoyage des logs et mutualisation des opérations de base de données
- suppression du code mort et des variables d’environnement obsolètes

## [0.3.0] - 2025-04-24

### Added
- ✅ HTML-based Telegram messages (replacing MarkdownV2)
- 🖼️ Image preview with clickable link via invisible `&#8205;`
- 🧠 Summary: cleaned HTML, 2-sentence max per article
- 📊 Rate limiting:
  - Global: max 20 messages/minute
  - Per-source: max 10 messages
- 🧩 Batching by source with 10s delay between each
- 📝 Escape handling with `html.escape` to avoid tag parsing issues

### Fixed
- ❌ No more `429 Too Many Requests` Telegram API errors
- 🧼 Removed `<p>` tags and fixed malformed Telegram HTML
- 🔍 Removed "Unknown Source" bug from terminal output

### Changed
- 🧠 Switched formatting logic from `notifier.py` to `main.py`
- 🎨 Refined Telegram layout for cleaner UX
- ⬆️ Logs improved: clearer, grouped, and minimal

---

## [0.2.0] - 2025-04-17

### Changed
- Refactored Telegram message structure:
  - Grouped articles by source
  - Added emoji headers and counts per digest
  - Styled formatting with MarkdownV2

### Fixed
- Avoided 429 rate-limit errors by reducing sends

### Removed
- `.pyc` and `__pycache__` files removed and `.gitignore` updated

---

## [0.1.0] - 2025-04-16

### Added
- Initial project setup: `sjvtdm`
- Modules: `rss_fetcher`, `notifier`, `twitter_fetcher`, etc.
- `README.md`, `CHANGELOG.md`, `.env` template
