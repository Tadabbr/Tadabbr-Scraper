from bs4 import BeautifulSoup, Tag
from bs4.element import PageElement
import re
import requests
import time
import sys
from requests.exceptions import RequestException


SKIPWORDS = ["ومنه قول","ومن ذلك قول","وكما قال الآخر"]
Unknown = "FiLLER"

# Compile regex patterns
DIACRITICS_REGEX = re.compile(r'[\u064B-\u065F\u0670]')
INDEX_REGEX = re.compile(r'nindex\.php\?[^\s]*')
BR_REGEX = re.compile(r'\s+')
SKIPWORDS_REGEX = re.compile("|".join([re.escape(word) for word in SKIPWORDS]))
TITLE_SURAH_REGEX = re.compile(r'تفسير سورة (\S+)')
TITLE_VERSE_REGEX = re.compile(r'قوله تعالى\s+"([^"]+)')

def remove_diacritics(word):
    return DIACRITICS_REGEX.sub('', word)

def clean_text(text: str, state:str="before") -> str:
    """Remove technical artifacts and normalize text"""
    text = remove_diacritics(text)  # remove diacritics for accurate cleaning
    text = INDEX_REGEX.sub('', text)
    text = re.sub(r'\[\s*ص:\s*\d+\s*\]', '', text)
    if state == "after":
        text = SKIPWORDS_REGEX.split(text)[0]
    return BR_REGEX.sub(' ', text).strip()

session = requests.Session()
session.headers.update({'User-Agent': '…'})

def scrape_islamweb_ayas(start_aya=24, limit=10, delay=1):
    """
    Generator function that scrapes IslamWeb content pages by incrementing aya numbers

    Args:
        start_aya (int): Starting aya number (default: 24)
        limit (int): Maximum number of pages to fetch (default: 10)
        delay (int): Delay between requests in seconds (default: 1)

    Yields:
        str: HTML content of each page
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    current_aya = start_aya
    fetched = 0

    while fetched < limit:
        url = f"https://www.islamweb.org/ar/library/content/50/{current_aya}"

        try:
            response = session.get(url, headers=headers)
            response.raise_for_status()

            # Check if page contains actual content (customize this check as needed)
            if "لا يوجد أي بيانات لعرضها" not in response.text:
                yield response.text
                fetched += 1
                current_aya += 1
            else:
                print(f"Stopping at aya {current_aya} - no content found")
                break

            time.sleep(delay)

        except RequestException as e:
            print(f"Error fetching aya {current_aya}: {str(e)}")
            break

def extract_quranic_info(soup):
    """
    Extracts Surah name and Quranic verse/phrase from metadata titles like:
    'إسلام ويب - تفسير الطبري - تفسير سورة الفاتحة - القول في تأويل قوله تعالى "اهدنا "- الجزء رقم1'

    Returns:
        tuple: (surah, verse)
    """
    title = soup.find('title').get_text()
    # Extract Surah name using the 'تفسير سورة' pattern
    surah_match = TITLE_SURAH_REGEX.search(title)
    surah = surah_match.group(1).strip() if surah_match else None

    # Extract verse/phrase using the 'قوله تعالى' pattern
    verse_match = TITLE_VERSE_REGEX.search(title)
    verse = verse_match.group(1).strip() if verse_match else None

    # Clean common suffixes from Surah name
    if surah:
        surah = re.sub(r'[-ـ]\s*الجزء.*$', '', surah).strip()
    try:
        verse = verse.split("-")[0]
    except:
        pass
    try:
        surah = surah.split("-")[0]
    except:
        pass

    return verse, surah

def count_br_between(start, end):
    count = 0
    current = start.next_element
    while current and current != end:
        if isinstance(current, Tag) and current.name == 'br':
            count += 1
        current = current.next_element
    return count


def extract_context(element: PageElement, direction: str) -> str:
    """Context extraction using structural boundaries"""
    context = []
    if element:
        current = element.previous_sibling if direction == 'before' else element.next_sibling
    else:
        return ""
    boundary_tags = ['p', 'div', 'center']
    limit = 0
    isdone = False
    while not isdone:
        if isinstance(current, Tag):
            if current.name == "br":
                limit += 1
            text = current.get_text(' ', strip=True)
        elif isinstance(current, str):
            text = current.strip()

        if text:
            context.append(text)
            context.append(" ")

        if limit >= 5:
            isdone = True
        if current:
            current = current.previous_sibling if direction == 'before' else current.next_sibling

        else:
            d = clean_text(''.join(reversed(context) if direction == 'before' else ''.join(context)))
            return d
    d = clean_text(''.join(reversed(context) if direction == 'before' else ''.join(context)),
                   state="before" if direction == "before" else "after")
    return d

def extract_poetry_data(html_content: str) -> list[dict]:
    soup = BeautifulSoup(html_content, 'lxml')
    results = []
    verse, surah_name = extract_quranic_info(soup)
    poems = ['']
    seen = set()
    # Find all poetry containers
    for poem in soup.find_all('p', align='center'):
        poetry_lines = ['']
        poetry: bs4.element.Tag = poem.find('font', color="#800080")
        poems.reverse
        try:
            t = any(clean_text(poetry.text).strip() == clean_text(x["context_after"]).strip() for x in results)
        except:
            t = False
        if any(remove_diacritics(poetry.text).strip() == remove_diacritics(x.strip()) for x in poems) or t:
            poems.reverse
            continue
        poetrynext = poetry.find_next("font", color="#800080")
        poetry_lines.append(poetry.text)
        if count_br_between(poetry, poetrynext) < 5:
            poetry_lines.append(poetrynext.text)

        combined_poetry = ''.join(poetry_lines).strip()
        # Extract poet and context
        poet_name = Unknown
        context_before = extract_context(poem, 'before')
        context_after = extract_context(poem, 'after')

        key = (context_after, combined_poetry, context_before)
        if key in seen:
            continue
        seen.add(key)
        results.append({
            'poet': poet_name,
            'poetry': clean_text(combined_poetry),
            'context_before': context_before,
            'context_after': context_after,
            'verse': verse,
            'surah': surah_name
        })

    return results

def write_output(data: list[dict], output_file: str):
    with open(output_file, 'w', encoding='utf-8') as f:
        added = []
        for item in data:
            key = item['context_after'] + "__" + item['poetry'] + "__" + item["context_before"]
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


if __name__ == "__main__":
    try:
        start = int(sys.argv[1])
    except:
        start = 20
    x = start
    for html_content in scrape_islamweb_ayas(start_aya=start, limit=10, delay=0.5):
        data = extract_poetry_data(html_content=html_content)
        added = write_output(data, f"output/poetery_PAGE[{x}].txt")
        print(f"Successfully processed {len(added)} in page {x}")
        x += 1
