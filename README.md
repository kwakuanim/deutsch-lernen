Deutsch Lernen: Lesen with current news
This package updates your existing single-page app while preserving Lesen, Vokabeln, Schreiben, Sprechen, Grammatik and Fortschritt.
Deploy to GitHub Pages
Back up your current repository and export your learning data under Fortschritt.
Upload `index.html`, `update_news.py`, and `.github/workflows/update-news.yml` into the root of your existing GitHub Pages repository, replacing `index.html` only after backup. Keep all other files.
Open Actions → Daily German news → Run workflow to create `news.json` for the first time.
Confirm that `news.json` appears in the repository root and that GitHub Pages publishes it next to `index.html`.
Reload your GitHub Pages website. News will load from `news.json` and refresh daily on the website as the workflow runs. GitHub Actions schedules can occasionally be delayed.
Notes
The 'Original-Kurztext' is the RSS summary, not the publisher's full article. The link opens the full article at its original source.
The C1 Lernfassung adds reading prompts and context questions; it does not invent additional reporting or copy the full publisher article.
Five comprehension questions are generated from the supplied summary and metadata. Some may be simple identification questions, not full C1 inference questions.
Double-click a word or select text and click 'Wort übersetzen'. Translation uses the external MyMemory service. Saved vocabulary and progress use localStorage in your browser.
Existing writing checks remain local by default. The optional LanguageTool feature sends writing text to an external service only when enabled.
If RSS feeds fail, the script retains an existing news.json; the app may show cached news or clearly labeled practice texts.
The app does not require an OpenAI API key or paid cloud backend.
