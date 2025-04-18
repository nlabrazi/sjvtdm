## [Unreleased] - 2025-04-18


- 🔧 chore: auto commit of modified files (2025-04-18 23:04)
- 🔧 chore: update changelog
- ✨ feat: group Telegram messages by source + cleanup pyc files
- 🔸 ✨ Improve Telegram notifications and logging
- ✨ feat: Add logging system and production-ready cron integration
- 🔧 chore: adding missing screenshot on readme
- 🔧 chore: Initial project structure with README, changelog, and base modules

## [Unreleased] - 2025-04-18


- ✨ feat: group Telegram messages by source + cleanup pyc files
- 🔸 ✨ Improve Telegram notifications and logging
- ✨ feat: Add logging system and production-ready cron integration
- 🔧 chore: adding missing screenshot on readme
- 🔧 chore: Initial project structure with README, changelog, and base modules


---

## 📄 `CHANGELOG.md`

```markdown
# 🗒️ CHANGELOG

## [0.1.0] - 2025-04-16

### Added
- Initial folder structure for the `sjvtdm` bot project
- Empty modules: `notifier`, `rss_fetcher`, `twitter_fetcher`, `sent_tracker`
- `.env` file for sensitive config
- `README.md` with project overview
- `CHANGELOG.md` for version tracking

## [0.2.0] - 2025-04-17

### Changed
- Refactored Telegram message formatting:
  - Grouped multiple articles by source into single messages
  - Added styled headers with emojis and article counts
  - Included a friendly introduction and conclusion in each digest

### Fixed
- Avoided Telegram API 429 errors (Too Many Requests) by reducing the number of messages sent

### Removed
- Deleted all `.pyc` and `__pycache__` files from the repo
- Updated `.gitignore` to ensure they are ignored going forward
