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
from urllib.parse import parse_qs

SKIPWORDS = ["ومنه قول", "ومن ذلك قول", "وكما قال الآخر", "ولآخر :"]
Unknown = "FiLLER"
LASTPOET = ["ثم قال :"]
UNPOET = ["القول في تأويل قوله", 'قوله : " "', "وتأويل قوله : ( )"]
UnknownIZE = ["وكما قال الآخر :"]
# Folder for downloaded HTML files
DOWNLOADS_FOLDER = "downloads"
PARSED_FOLDER = "output"


with open("surah_number_map.json", "r", encoding="utf-8") as f:
    SURAHNUMBERHASHMAP = json.load(f)


# Flag to control downloading mode
download_only = False  # Set to True to download without parsing

logger.add("debug.log", rotation="100 MB", retention="7 days", level="DEBUG")

AYAT = json.load(open("ayat.json"))


def clean_text(text: str, state: str = "before") -> str:
    text = araby.strip_diacritics(text)
    text = text.replace(":", "").replace(",", "").replace("،", "").strip()
    text = re.sub(r"nindex\.php\?[^\s]*", "", text)
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




def isayanumbering(s:str) -> bool: # is (25) for example
    s = s.strip().replace(" ","")
    return bool(re.match(r'^\(\d+\)$', s))

global LASTKEYS 
LASTKEYS = []

def get_ayat(soup,surah):
    global LASTKEYS
    # Extract all elements with class 'quran'
    quran_elements = soup.find_all('a', href="#docu")
    for i,element in enumerate(quran_elements):
        sibl = None 
        docu_element = element

        while element and not sibl:
            element = element.next_element
            if element and isinstance(element, str) and element.strip():
                # Make sure it's not inside the original element
                if not docu_element in element.parents:
                    sibl = element.strip()
        if sibl.count(")") > 1 or (not isayanumbering(s=sibl) and sibl.count(")") == 1):
            quran_elements = quran_elements[:i+1]
            break
    
    ayat = []
    keys = []

    for i,element in enumerate(quran_elements):
        # Get the `onclick` attribute value
        onclick_js = element.get('onclick', '')
        
        # Extract the `src` from the IFRAME string
        # Split the string to isolate the src value
        if "src=" in onclick_js:
            # Split after "src='" and then split again at the next "'"
            src_value = onclick_js.split("ayatafseer.php?")[1].split("'")[0]
            params = parse_qs(src_value)
            surano = params.get("surano", [None])[0]
            ayano = params.get("ayano", [None])[0]
            surano = str(surano).strip().replace("\\","")
            ayano = str(ayano).strip().replace("\\","")
#            logger.info(f"surahno: {surano}")   
#            logger.info(f"ayano: {ayano}")
            try:
                surano = int(surano)
                ayano = int(ayano)
            except Exception as e:
#                logger.error(e)
                continue

            if int(SURAHNUMBERHASHMAP[surah.strip()]) != int(surano):
                continue
            
            key = f"{surano}:{ayano}"
            LASTKEYS = [key]
            keys.append(key)

    if len(keys) == 0:
        return LASTKEYS
    return list(set(keys))


def extract_quranic_info(soup,is_keys:bool=False):
    try:
        title = soup.find("title").get_text()
        tparts = title.split("-")
        surah = tparts[2].strip().replace("تفسير سورة", "")

        verse = False
        if surah:
            surah = surah.strip()
        if surah == "القول في تأويل البسملة".strip():
            surah = "الفاتحة"
        surah = araby.strip_diacritics(surah)
        try:
            if not is_keys:
                verse = get_ayat(soup=soup,surah=surah)
        except Exception as e:
            logger.error(e)
            pass

#        logger.info(f"VERSE -> {verse}")
        if not is_keys:
            return verse, surah
        else:
            return verse,surah

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



def extract_poetry_data(
    html_content: str, verse_keys
) -> list[dict]:
    
    try:
        soup = BeautifulSoup(html_content, "lxml")

        results = []
        if not verse_keys:
            verse_keys, surah_name = extract_quranic_info(soup,is_keys=False)
        else:
            _, surah_name = extract_quranic_info(soup,is_keys=True)
        

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
            poet_name = extract_poet(poem)
            context_before = clean_text(extract_context(poem, "before"))
            context_after = clean_text(extract_context(poem, "after"))
            poet_name = clean_text(poet_name)
            for word in LASTPOET:
                if word in context_before or clean_text(word) == context_before:
                    if poet_name == Unknown and results:
                        poet_name = results[-1]["poet"]

            for word in UnknownIZE:
                if word in context_before:
                    poet_name = Unknown

            for word in UNPOET:
                if word.strip() == poet_name.strip():
                    poet_name = Unknown

            poet_name = clean_text(poet_name)

            results.append(
                {
                    "poet": poet_name,
                    "poetry": clean_text(combined_poetry),
                    "context_before": context_before,
                    "context_after": context_after,
                    "surah": surah_name,
                    "tafsir": "تفسير الطبري = جامع البيان عن تأويل آي القرآن",
                    "surah_keys": verse_keys,
                }
            )
        return results
    except Exception as e:
        logger.exception("Failed to extract poetry data")
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
                UNIQUE(context_after, poetry, context_before,verse_key,verse)
            )
        """
        )

        inserted_count = 0
        for item in data:
            for key in item["surah_keys"]:
                try:
                    verse = get_verse_text(int(key.split(":")[0]),int(key.split(":")[1]))
                except Exception as e:
                    logger.error(f"Error: {e} , ITEM:{item}")
                    continue
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
                            verse,
                            item["surah"],
                            item["tafsir"],
                            key,
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


def parse_all_downloaded():
    os.makedirs(PARSED_FOLDER, exist_ok=True)
    files = sorted(
        (f for f in os.listdir(DOWNLOADS_FOLDER) if f.endswith(".html")),
        key=lambda name: int(re.search(r"page_(\d+)\.html", name).group(1)),
    )
#    logger.info(f"Found {len(files)} downloaded pages to process.")

    seen = set()
    total_results = []
    RESULTS_COUNT = 0 
    ftov = {'page_16.html':["1:1"],'page_17.html':["1:1"],'page_18.html':["1:1"],'page_19.html':["1:2"]}
    #files = ["page_30.html","page_31.html"]
    for i, file in enumerate(files):
        logger.info(file)
        if i % 500 == 0:
            output_file = os.path.join("output", f"poetery.db")
            RESULTS_COUNT += len(total_results)
            save_to_sqlite(total_results)
            total_results = []
        file_path = os.path.join(DOWNLOADS_FOLDER, file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                html = f.read()
            if ftov.get(file):
                data = extract_poetry_data(html,verse_keys=ftov.get(file))
            else:
                data = extract_poetry_data(html,verse_keys=None)
            if data:
                for item in data:
                    total_results.append(item)
            else:
                continue
        except Exception as e:
            logger.exception(f"Error parsing {file}")
    save_to_sqlite(total_results)
    return RESULTS_COUNT

if __name__ == "__main__":
    times = []
    all_runs = 1
    x = 0
    UNPOET = [clean_text(word) for word in UNPOET]
    UnknownIZE = [clean_text(word) for word in UnknownIZE]
    LASTPOET = [clean_text(word) for word in LASTPOET]

    num = parse_all_downloaded()
    print(f"SCRAPED {num} POETS")
