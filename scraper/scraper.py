import aiohttp
import asyncio
import re
import time
import sys
from bs4 import BeautifulSoup, Tag
from bs4.element import PageElement

SKIPWORDS = ["ومنه قول", "ومن ذلك قول", "وكما قال الآخر"]
Unknown = "FiLLER"

def remove_diacritics(word):
    return re.sub(r'[\u064B-\u065F\u0670]', '', word)

def clean_text(text: str, state: str = "before") -> str:
    text = remove_diacritics(text)
    text = re.sub(r'nindex\.php\?[^\s]*', '', text)
    text = re.sub(r'\[\s*ص:\s*\d+\s*\]', '', text)
    if state == "after":
        for sword in SKIPWORDS:
            text = text.split(sword)[0]
    return re.sub(r'\s+', ' ', text).strip()

def count_br_between(start, end):
    count = 0
    current = start.next_element
    while current and current != end:
        if isinstance(current, Tag) and current.name == 'br':
            count += 1
        current = current.next_element
    return count

def extract_quranic_info(soup):
    title = soup.find('title').get_text()
    surah_match = re.search(r'تفسير سورة (\S+)', title)
    surah = surah_match.group(1).strip() if surah_match else None
    verse_match = re.search(r'قوله تعالى\s+"([^"]+)', title)
    verse = verse_match.group(1).strip() if verse_match else None
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

def extract_context(element: PageElement, direction: str) -> str:
    context = []
    if element:
        current = element.previous_sibling if direction == 'before' else element.next_sibling
    else:
        return ""
    limit = 0
    isdone = False
    while not isdone:
        if isinstance(current, Tag):
            if current.name == "br":
                limit += 1
            text = current.get_text(' ', strip=True)
        elif isinstance(current, str):
            text = current.strip()
        else:
            text = ""
        if text:
            context.append(text)
            context.append(" ")
        if limit >= 5:
            isdone = True
        if current:
            current = current.previous_sibling if direction == 'before' else current.next_sibling
        else:
            break
    d = clean_text(''.join(reversed(context) if direction == 'before' else ''.join(context)), state="before" if direction == "before" else "after")
    return d

def extract_poetry_data(html_content: str) -> list[dict]:
    soup = BeautifulSoup(html_content, 'lxml')
    results = []
    verse, surah_name = extract_quranic_info(soup)
    poems = ['']
    seen = set()
    for poem in soup.find_all('p', align='center'):
        poetry_lines = ['']
        poetry = poem.find('font', color="#800080")
        try:
            t = any(clean_text(poetry.text).strip() == clean_text(x["context_after"]).strip() for x in results)
        except:
            t = False
        if any(remove_diacritics(poetry.text).strip() == remove_diacritics(x.strip()) for x in poems) or t:
            continue
        poetrynext = poetry.find_next("font", color="#800080")
        poetry_lines.append(poetry.text)
        if poetrynext and count_br_between(poetry, poetrynext) < 5:
            poetry_lines.append(poetrynext.text)
        combined_poetry = ''.join(poetry_lines).strip()
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
            f.write("\n" + "="*80 + "\n\n")
        return added

# ---------------------
# ASYNC SECTION BELOW
# ---------------------
async def fetch(session, url):
    try:
        async with session.get(url) as response:
            text = await response.text()
            if "لا يوجد أي بيانات لعرضها" in text:
                return None
            return text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

async def fetch_all(start: int, limit: int) -> list[str]:
    urls = [f"https://www.islamweb.org/ar/library/content/50/{start + i}" for i in range(limit)]
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        tasks = [fetch(session, url) for url in urls]
        html_pages = await asyncio.gather(*tasks)
        return [html for html in html_pages if html]

# -------------
# MAIN LOGIC
# -------------
if __name__ == "__main__":
    try:
        start = int(sys.argv[1])
    except:
        start = 20

    limit = 10
    html_pages = asyncio.run(fetch_all(start=start, limit=limit))
    for i, html in enumerate(html_pages):
        data = extract_poetry_data(html)
        added = write_output(data, f"output/poetery_PAGE[{start+i}].txt")
        print(f"Successfully processed {len(added)} items on page {start+i}")
