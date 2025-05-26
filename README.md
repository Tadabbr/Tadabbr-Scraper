# جارفُ الشعر الإسلامي

تم تصميم هذا المشروع لـ **استخراج الأبيات الشعرية العربية المضمنة في شروحات آيات القرآن**، مع الحفاظ على السياق الذي تم فيه ذكر كل بيت.

تعمل الأداة عن طريق تصفح الصفحات المحمّلة مسبقًا بصيغة HTML من قسم التفسير في موقع إسلام ويب,وتحديد المقاطع الشعرية التي استشهد بها العلماء لدعم أو توضيح تفسيراتهم. وبالإضافة إلى الأبيات، تقوم الأداة بجمع:

- **اسم الشاعر** (إن توفّر)،  
- **السياق المحيط بالبيت** (قبله وبعده)،  
- **الآية القرآنية المحددة** المرتبط بها البيت،  
- و**بيانات السورة والآية** (رقم السورة والآية).

ثم تُنظَّم جميع البيانات المستخرجة وتُحفظ في قاعدة بيانات محلية باستخدام SQLite، مما يسهّل استكشاف هذه الإشارات الشعرية أو البحث فيها أو تحليلها في المستقبل.

# Islamic Poetry Scraper

This project is designed to **extract poetic references from the Tafsir (Quranic exegesis) pages on Islamweb**. Specifically, it focuses on pulling **Arabic poetry embedded within the interpretations of Quranic verses**, preserving the context in which each poem is quoted.

The scraper works by navigating through pre-downloaded HTML pages from Islamweb's Tafsir section—especially *Tafsir al-Tabari*—and identifying poetic segments that scholars have cited to support or illustrate their interpretations. Along with the poetry, the script captures:

- The **name of the poet** (when available),
- The **context surrounding the poem** (before and after),
- The **specific Quranic verse** the poem is linked to,
- And the **Surah and Ayah (chapter and verse)** metadata.

All extracted data is then organized and saved into a local SQLite database, making it easy to explore, search, or analyze these poetic references in the future.
