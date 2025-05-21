# Islamic Poetry Scraper

This project is designed to **extract poetic references from the Tafsir (Quranic exegesis) pages on Islamweb**. Specifically, it focuses on pulling **Arabic poetry embedded within the interpretations of Quranic verses**, preserving the context in which each poem is quoted.

The scraper works by navigating through pre-downloaded HTML pages from Islamweb's Tafsir section—especially *Tafsir al-Tabari*—and identifying poetic segments that scholars have cited to support or illustrate their interpretations. Along with the poetry, the script captures:

- The **name of the poet** (when available),
- The **context surrounding the poem** (before and after),
- The **specific Quranic verse** the poem is linked to,
- And the **Surah and Ayah (chapter and verse)** metadata.

All extracted data is then organized and saved into a local SQLite database, making it easy to explore, search, or analyze these poetic references in the future.
