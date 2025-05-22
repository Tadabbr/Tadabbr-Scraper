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

logger.add("debug.log", rotation="1 MB", retention="7 days", level="DEBUG")

AYAT = json.load(open("ayat.json"))


def clean_text(text: str, state: str = "before") -> str:
    text = araby.strip_diacritics(text)
    text = text.replace(":", "").replace(",", "").replace("،", "").strip()
    text = re.sub(r"nindex\.php\?[^\s]*", "", text)
    # text = re.sub(r"\[\s*ص:\s*\d+\s*\]", "", text)
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




def normalize(x):
    if type(x) == list: 
        x = " ".join(x) # stringify 

    # remove arabic diacritics:
    x = str(araby.strip_diacritics(x))
    # remove spaces and concatenate 
    x = x.replace(" ","")
    return x

aya_index = 1
aya_builder_list = []
last_surah_index = 1
def assign_ayat(current_verse:str,surah_name:str)-> tuple[str,str]: #aya,key
    global aya_index
    global aya_builder_list
    global last_surah_index
    logger.info(f"{'=' * 10}")

    # surah number in the quran
    SURAHN = SURAHNUMBERHASHMAP[surah_name.strip()] 
    
    # reset aya index if surah changes
    if SURAHN != last_surah_index:
        exit()
        aya_index = 1
        last_surah_index = SURAHN
    # get the target verse
    target = get_verse_text(surah_number=SURAHN,ayah_number=aya_index)

    # add the current aya to the aya builder list 
    aya_builder_list.append(current_verse)
    # normalize target and current verse
    target_check = normalize(target)
    current_check = normalize(aya_builder_list)

    # check if the target is in the current check
    logger.info(f"TARGET -> {target}")
    logger.info(f"BUILDER_LIST -> {" ".join(aya_builder_list)}")
    logger.info(f"TARGET CHECK -> {target_check}")
    logger.info(f"AYA CHECK -> {current_check}")
    logger.info(f"AYA INDEX -> {aya_index}")
    logger.info(f"SURAH INDEX -> {SURAHN}")

     # Get first meaningful word of target (space-based before normalization)
    target_first_word = normalize(target.split()[0]) if ' ' in target else target_check

    # 1. Word Alignment Check
    if not current_check.startswith(target_first_word):
        # Find if target's first word exists later in current_check
        if target_first_word in current_check:
            # Split accumulated text at first occurrence of target word
            split_index = current_check.find(target_first_word)
            realigned_text = current_check[split_index:]
            
            # Reset builder with realigned content  
            aya_builder_list = [realigned_text]
            current_check = realigned_text
            logger.info(f"Realigned to target start at index {split_index}")

    # 2. Length Overflow Check
    if len(current_check) > len(target_check) and target_check not in current_check:
        logger.warning(f"Skipping aya {aya_index} - Length overflow without target match")
        aya_index += 1
        key = f"{SURAHN}:{aya_index}"
        aya_builder_list.clear()
        return "", key


    logger.info(f"{'=' * 10}")

    # check if the target is in the current check
    if target_check in current_check:
        # reset aya_builder_list
        aya_builder_list.clear()
        # make key
        key = f"{SURAHN}:{aya_index}"
        # increment aya
        aya_index += 1
        return target,key
    else:
        key = f"{SURAHN}:{aya_index}"

        return target,key
        


def extract_poetry_data(
    html_content: str, html_content_next_page: str = ""
) -> list[dict]:
    
    try:
        soup = BeautifulSoup(html_content, "lxml")

        results = []
        verse_word, surah_name = extract_quranic_info(soup)
        # get full aya
        verse,verse_key = assign_ayat(current_verse=verse_word,surah_name=surah_name)
        

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
                    "verse": verse,
                    "surah": surah_name,
                    "tafsir": "تفسير الطبري = جامع البيان عن تأويل آي القرآن",
                    "surah_key": verse_key,
                    "word":verse_word
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
                word TEXT,
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
                    (poet, poetry, context_before, context_after, verse, surah, tafsir,verse_key,word)
                    VALUES (?, ?, ?, ?, ?, ?, ?,?,?)
                """,
                    (
                        item["poet"],
                        item["poetry"],
                        item["context_before"],
                        item["context_after"],
                        item["verse"],
                        item["surah"],
                        item["tafsir"],
                        item["surah_key"],
                        item["word"]
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


if __name__ == "__main__":
    times = []
    all_runs = 1
    x = 0
    UNPOET = [clean_text(word) for word in UNPOET]
    UnknownIZE = [clean_text(word) for word in UnknownIZE]
    LASTPOET = [clean_text(word) for word in LASTPOET]

    parse_all_downloaded()
