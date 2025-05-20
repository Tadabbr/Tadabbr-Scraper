import aiohttp
import asyncio
import re
import time
import sys
from bs4 import BeautifulSoup, Tag
from bs4.element import PageElement
from loguru import logger
import os
import random
import json
import sqlite3
from pprint import pp as print
import pyarabic.araby as araby
from difflib import SequenceMatcher
ALLPOEMS = 0
SKIPWORDS = ["ومنه قول", "ومن ذلك قول", "وكما قال الآخر", "ولآخر :"]
Unknown = "FiLLER"
LASTPOET = ["ثم قال :"]
UNPOET = ["القول في تأويل قوله",'قوله : " "',"وتأويل قوله : ( )"]
UnknownIZE = ["وكما قال الآخر :"]
# Folder for downloaded HTML files
DOWNLOADS_FOLDER = "downloads"
PARSED_FOLDER = "output"
SURAHNUMBERHASHMAP = {
    "الفاتحة": 1,
    "البقرة": 2,
    "آل عمران": 3,
    "النساء": 4,
    "المائدة": 5,
    "الأنعام": 6,
    "الأعراف": 7,
    "الأنفال": 8,
    "التوبة": 9,
    "يونس": 10,
    "هود": 11,
    "يوسف": 12,
    "الرعد": 13,
    "إبراهيم": 14,
    "الحجر": 15,
    "النحل": 16,
    "الإسراء": 17,
    "الكهف": 18,
    "مريم": 19,
    "طه": 20,
    "الأنبياء": 21,
    "الحج": 22,
    "المؤمنون": 23,
    "النور": 24,
    "الفرقان": 25,
    "الشعراء": 26,
    "النمل": 27,
    "القصص": 28,
    "العنكبوت": 29,
    "الروم": 30,
    "لقمان": 31,
    "السجدة": 32,
    "الأحزاب": 33,
    "سبإ": 34,
    "فاطر": 35,
    "يس": 36,
    "الصافات": 37,
    "ص": 38,
    "الزمر": 39,
    "غافر": 40,
    "فصلت": 41,
    "الشورى": 42,
    "الزخرف": 43,
    "الدخان": 44,
    "الجاثية": 45,
    "الأحقاف": 46,
    "محمد": 47,
    "الفتح": 48,
    "الحجرات": 49,
    "ق": 50,
    "الذاريات": 51,
    "الطور": 52,
    "النجم": 53,
    "القمر": 54,
    "الرحمن": 55,
    "الواقعة": 56,
    "الحديد": 57,
    "المجادلة": 58,
    "الحشر": 59,
    "الممتحنة": 60,
    "الصف": 61,
    "الجمعة": 62,
    "المنافقون": 63,
    "التغابن": 64,
    "الطلاق": 65,
    "التحريم": 66,
    "الملك": 67,
    "القلم": 68,
    "الحاقة": 69,
    "المعارج": 70,
    "نوح": 71,
    "الجن": 72,
    "المزمل": 73,
    "المدثر": 74,
    "القيامة": 75,
    "الإنسان": 76,
    "المرسلات": 77,
    "النبأ": 78,
    "النازعات": 79,
    "عبس": 80,
    "التكوير": 81,
    "الإنفطار": 82,
    "المطففين": 83,
    "الإنشقاق": 84,
    "البروج": 85,
    "الطارق": 86,
    "الأعلى": 87,
    "الغاشية": 88,
    "الفجر": 89,
    "البلد": 90,
    "الشمس": 91,
    "الليل": 92,
    "الضحى": 93,
    "الشرح": 94,
    "التين": 95,
    "العلق": 96,
    "القدر": 97,
    "البينة": 98,
    "الزلزلة": 99,
    "العاديات": 100,
    "القارعة": 101,
    "التكاثر": 102,
    "العصر": 103,
    "الهمزة": 104,
    "الفيل": 105,
    "قريش": 106,
    "الماعون": 107,
    "الكوثر": 108,
    "الكافرون": 109,
    "النصر": 110,
    "المسد": 111,
    "الإخلاص": 112,
    "الفلق": 113,
    "الناس": 114
}
vs = []
aya = 0
last_surah = ""
lastvs = ""
surah_key = ""
target = ""
# Flag to control downloading mode
download_only = False  # Set to True to download without parsing

logger.add("debug.log", rotation="1 MB", retention="7 days", level="DEBUG")

AYAT = json.load(open("docs/ayat.json"))


def clean_text(text: str, state: str = "before") -> str:
    text = araby.strip_diacritics(text)
    text = text.replace(":","").replace(",","").replace("،","").strip()
    text = re.sub(r"nindex\.php\?[^\s]*", "", text)
    #text = re.sub(r"\[\s*ص:\s*\d+\s*\]", "", text)
    if state == "after":
        for sword in SKIPWORDS:
            text = text.split(sword)[0]
    return re.sub(r"\s+", " ", text).strip()


def count_br_between(start, end):
    count = 0
    current = start.next_element
    while current and current != end:
        if isinstance(current, Tag) and current.name == "br":
            count += 1
        current = current.next_element
    return count


def extract_quranic_info(soup):
    try:
        title = soup.find("title").get_text()
        tparts = title.split("-")
        surah = tparts[2].strip().replace("تفسير سورة", "")
        
        if surah:
            surah = surah.strip()
        if surah == "القول في تأويل البسملة".strip():
            surah = "الفاتحة"
        aya = tparts[3].strip()
        ayaparts = aya.split('"')
        verse = ayaparts[1].strip()
        return verse, araby.strip_diacritics(surah)
    except Exception as e:
        logger.exception("Error extracting Quranic info", e)
        return None, None


def extract_context(element: PageElement, direction: str) -> str:
    context = []
    if element:
        current = (
            element.previous_sibling if direction == "before" else element.next_sibling
        )
    else:
        return ""
    limit = 0
    isdone = False
    while not isdone:
        try:
            if isinstance(current, Tag):
                if current.name == "br":
                    limit += 1
                text = current.get_text(" ", strip=True)
            elif isinstance(current, str):
                text = current.strip()
            else:
                text = ""
            if text:
                context.append(text)
                context.append(" ")
            if limit >= 5:
                isdone = True

            current = (
                current.previous_sibling
                if direction == "before"
                else current.next_sibling
            )
        except Exception as e:
            break
    try:
        joined = (
            "".join(reversed(context)) if direction == "before" else "".join(context)
        )
        return clean_text(joined, state=direction)
    except Exception as e:
        logger.exception("Error cleaning context")
        return ""


def extract_poet(element: PageElement) -> str:
    """Dynamic poet extraction using Arabic naming patterns"""

    # Look for poet in previous 5 elements to avoid overshooting

    limit = 0

    isdone = False

    while not isdone:

        try:

            element = element.previous_sibling

        except:

            return Unknown

        try:

            if element.name == "br":

                limit += 1

                continue

        except AttributeError:

            return Unknown

        if isinstance(element, Tag) and any(element.name == x for x in ["span", "a"]):

            limit += float("inf")

            # Clean nested elements and check for name patterns

            for nested in element.find_all(["span", "a"]):

                nested.decompose()

            text = element.get_text(" ", strip=True)

            for word in UNPOET:

                if word in text:

                    continue

            if len(text) == 0:

                return Unknown

            return clean_text(text)

        if limit > 3:

            isdone = True

    return Unknown

ALLVSZ = []

def get_verse_text(surah_number, ayah_number):
    try:
        # Validate that surah_number is within the valid range
        if not (1 <= surah_number <= len(AYAT)):
            return f"Error: Surah number {surah_number} is out of range. It should be between 1 and {len(AYAT)}."
        
        # Get the surah based on the surah_number (1-based index)
        surah = AYAT[surah_number - 1]

        # Validate that ayah_number is within the valid range for the selected surah
        if not (1 <= ayah_number <= surah["total_verses"]):
            return f"Error: Ayah number {ayah_number} is out of range for Surah {surah['name']} ({surah_number}). It should be between 1 and {surah['total_verses']}."
        
        # Return the text of the specific verse
        return surah["verses"][ayah_number - 1]["text"]

    except IndexError:
        # Catch any unexpected IndexError if data is malformed
        return f"Error: Invalid data structure for Surah {surah_number}, Ayah {ayah_number}."

    except Exception as e:
        # Catch any other unexpected errors
        return f"Error: An unexpected error occurred: {str(e)}."



def normalize(s):
    return re.sub(r"\s+", " ", araby.strip_diacritics(s)).replace(" ","").strip()



def similar(a, b):
    return a in b

def extract_poetry_data(
    html_content: str, html_content_next_page: str = ""
) -> list[dict]:
    global ALLPOEMS
    global AYAT
    global vs
    global last_surah
    global lastvs
    global surah_key
    global aya
    global target
    try:
        soup = BeautifulSoup(html_content, "lxml")
           
        results = []
        verse, surah_name = extract_quranic_info(soup)
        SURAHN = SURAHNUMBERHASHMAP[surah_name.strip()]
           
        if verse is None or surah_name is None:
            return results
        
        if surah_name != last_surah:
                vs = []
                aya = 1
                last_surah = surah_name
        if verse in lastvs:
            aya - 1 
            SURAHN = SURAHNUMBERHASHMAP[surah_name.strip()]
            
        if normalize(verse).strip() != lastvs.strip():
            vs.append(normalize(verse))
            lastvs = normalize(verse)
        for i in [aya,aya-1,aya+1]:
            target = normalize(get_verse_text(SURAHN,i))
            logger.info("SURAHNAME: " + str(surah_name))
            logger.info("AYA: "+ str(aya))
            logger.info("TARGET: "+ str(normalize(target)))
            logger.info("VS: "+ str(normalize("".join(vs))))
            logger.info("LAST VS: " + str(lastvs))
            logger.info("SIMILAR: "+ str(similar(target,"".join(vs))))
            if similar(target,"".join(vs)): 
                verse = " ".join(vs).strip()
                if verse not in ALLVSZ:
                    vs = []
                    lastvs = verse
                    aya = i
                    aya  += 1 # aya complete go to next aya
                    ALLVSZ.append(verse)

        if lastvs == "":
            lastvs = normalize(verse)
                
        surah_key= f"{SURAHN}:{aya}"
        poems = [""]
        seen = set()  # Track seen poems by context + poetry
        for poem in soup.find_all("p", align="center"):
            
            poetry_lines = [""]
            poetry = poem.find("font", color="#800080")
            if not poetry:
                continue
            try:
                t = any(
                    clean_text(poetry.text).strip()
                    == clean_text(x["context_after"]).strip()
                    for x in results
                )
            except:
                t = False
            if (
                any(
                    araby.strip_diacritics(poetry.text).strip()
                    == araby.strip_diacritics(x.strip())
                    for x in poems
                )
                or t
            ):
                continue
            poetrynext = poetry.find_next("font", color="#800080")
            poetry_lines.append(poetry.text)
            if poetrynext and count_br_between(poetry, poetrynext) < 5:
                poetry_lines.append(poetrynext.text)
            combined_poetry = "\n".join(poetry_lines).strip()
            ALLPOEMS+=1
            poet_name = extract_poet(poem)
            context_before = clean_text(extract_context(poem, "before"))
            context_after = clean_text(extract_context(poem, "after"))
            poet_name = clean_text(poet_name)
            for word in LASTPOET:
                if word in context_before or clean_text(
                    word
                ) == context_before:
                    if poet_name == Unknown and results:
                        poet_name = results[-1]["poet"]

            for word in UnknownIZE:
                if word in context_before:
                    poet_name = Unknown
            
            for word in UNPOET:
                if word.strip() == poet_name.strip():
                    poet_name = Unknown
        
            poet_name = clean_text(poet_name)
            # Use a tuple of the combined data as the key to avoid duplicates
            


            results.append(
                {
                    "poet": poet_name,
                    "poetry": clean_text(combined_poetry),
                    "context_before": context_before,
                    "context_after": context_after,
                    "verse": target,
                    "surah": surah_name,
                    "tafsir": "تفسير الطبري = جامع البيان عن تأويل آي القرآن",
                    "surah_key":surah_key
                }
            )
        return results
    except Exception as e:
        logger.exception("Failed to extract poetry data")
        return []


def write_output(data: list[dict], output_file: str):
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        added = []
        with open(output_file, "w", encoding="utf-8") as f:
            for item in data:
                key = (
                    item["context_after"]
                    + "__"
                    + item["poetry"]
                    + "__"
                    + item["context_before"]
                )
                if key in added:
                    continue
                added.append(key)
                f.write(f"Poet: {item['poet']}\n")
                f.write(f"poetry: {item['poetry']}\n")
                f.write(f"Context Before: {item['context_before']}\n")
                f.write(f"Context After: {item['context_after']}\n")
                f.write(f"verse: {item['verse']}\n")
                f.write(f"surah: {item['surah']}\n")
                f.write("\n" + "=" * 80 + "\n\n")
        return added
    except Exception as e:
        logger.exception(f"Error writing to file {output_file}")
        return []


def save_to_sqlite(
    data: list[dict], db_path: str = "output/poetry.db", table_name: str = "poems"
):

    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poet TEXT,
                poetry TEXT,
                context_before TEXT,
                context_after TEXT,
                verse TEXT,
                surah TEXT,
                tafsir TEXT,
                verse_key TEXT,
                UNIQUE(context_after, poetry, context_before)
            )
        """
        )

        inserted_count = 0
        for item in data:
            try:
                cursor.execute(
                    f"""
                    INSERT OR IGNORE INTO {table_name} 
                    (poet, poetry, context_before, context_after, verse, surah, tafsir,verse_key)
                    VALUES (?, ?, ?, ?, ?, ?, ?,?)
                """,
                    (
                        item["poet"],
                        item["poetry"],
                        item["context_before"],
                        item["context_after"],
                        item["verse"],
                        item["surah"],
                        item["tafsir"],
                        item["surah_key"]
                    ),
                )
                if cursor.rowcount > 0:
                    inserted_count += 1
            except Exception as inner_e:
                logger.exception("Insert failed for item", inner_e)
                continue

        conn.commit()
        conn.close()
        logger.info(f"Saved {inserted_count} new poems to {db_path}")
        return inserted_count
    except Exception as e:
        logger.exception(f"Failed to save data to SQLite {db_path}")
        return 0


async def fetch(session, url):
    try:
        async with session.get(url) as response:
            text = await response.text()
            if "لا يوجد أي بيانات لعرضها" in text:
                return None
            return text
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


async def fetch_all(start: int, limit: int) -> list[str]:
    urls = [
        f"https://www.islamweb.com/ar/library/content/50/{start + i}"
        for i in range(limit)
    ]
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        html_pages = []
        total_poems = 0  # Track the total number of poems
        # Handle the batches of 30 requests
        for i in range(0, len(urls), 30):
            batch_urls = urls[i : i + 30]
            tasks = [fetch(session, url) for url in batch_urls]
            batch_html_pages = await asyncio.gather(*tasks)
            html_pages.extend([html for html in batch_html_pages if html])

            # Count poems in the current batch
            for html in batch_html_pages:
                soup = BeautifulSoup(html, "lxml")
                poems = soup.find_all("p", align="center")
                total_poems += len(poems)

            # Sleep for 1 to 2 seconds after each batch
            await asyncio.sleep(random.uniform(1, 2))

        logger.info(f"Total poems expected: {total_poems}")
        return html_pages, total_poems


def write_output_json(data: list[dict], output_file: str):
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        seen_keys = set()
        deduped_data = []

        for item in data:
            key = (
                item["context_after"]
                + "__"
                + item["poetry"]
                + "__"
                + item["context_before"]
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped_data.append(item)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(deduped_data, f, ensure_ascii=False, indent=2)
        return deduped_data
    except Exception as e:
        logger.exception(f"Error writing JSON to file {output_file}")
        return []


def parse_all_downloaded():
    os.makedirs(PARSED_FOLDER, exist_ok=True)

    files = sorted(
        (f for f in os.listdir(DOWNLOADS_FOLDER) if f.endswith(".html")),
        key=lambda name: int(re.search(r"page_(\d+)\.html", name).group(1)),
    )
    logger.info(f"Found {len(files)} downloaded pages to process.")

    seen = set()
    total_results = []
    added = 0
    
    for i, file in enumerate(files):
        logger.info(file)
        output_file = os.path.join("output", f"poetery.db")
        added += save_to_sqlite(total_results)
        total_results = []
        file_path = os.path.join(DOWNLOADS_FOLDER, file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                html = f.read()
            data = extract_poetry_data(html)
            if data:
                for item in data:
                        total_results.append(item)
            else:
                continue
        except Exception as e:
            logger.exception(f"Error parsing {file}")


async def download_pages(start: int, limit: int):
    urls = [
        f"https://www.islamweb.org/ar/library/content/50/{start + i}"
        for i in range(limit)
    ]
    os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        for i, url in enumerate(urls):
            file_name = os.path.join(DOWNLOADS_FOLDER, f"page_{start + i}.html")
            if os.path.exists(file_name):
                logger.info(f"Skipping download of {file_name} as it already exists.")
                continue
            html_content = await fetch(session, url)
            if html_content:
                with open(file_name, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"Downloaded {file_name}")


if __name__ == "__main__":
    times = []
    all_runs = 1
    x = 0
    UNPOET = [clean_text(word) for word in UNPOET]
    UnknownIZE = [clean_text(word) for word in UnknownIZE]
    LASTPOET = [clean_text(word) for word in LASTPOET]


    for i in range(all_runs):
        s = time.time()
        try:
            start = int(sys.argv[1])
        except:
            start = 0

        limit = 20

        if start == 0:

            parse_all_downloaded()
            logger.info(ALLPOEMS)
        if download_only:
            # Download all pages first
            asyncio.run(download_pages(start=start, limit=limit))

        else:
            # Parse downloaded pages
            try:

                x = f"/home/iq/code/shawahid/scraper/downloads/page_{start+1}.html"
                data = extract_poetry_data(
                    open(
                        f"/home/iq/code/shawahid/scraper/downloads/page_{start}.html",
                        "r",
                    ).read()
                )
                added = save_to_sqlite(data)
                logger.info(f"Successfully processed {added} items on page {start+i}")

            except Exception as e:
                logger.exception("Top-level failure in main loop")
