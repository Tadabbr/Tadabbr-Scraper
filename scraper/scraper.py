from bs4 import BeautifulSoup, Tag
from bs4.element import PageElement
import re
import requests
import time
import sys
from requests.exceptions import RequestException

Unknown = "Unknown"
SKIPWORDS = ["ومنه قول","ومن ذلك قول","وكما قال الآخر","ويقول :","كما قال الشاعر"]
LASTPOET = ["ثم قال :"]
UNPOET = ["القول في تأويل قوله"]
UnknownIZE = ["وكما قال الآخر :"]
def remove_diacritics(word):
    return re.sub(r'[\u064B-\u065F\u0670]', '', word)

    


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
            response = requests.get(url, headers=headers)
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
    surah_match = re.search(r'تفسير سورة (\S+)', title)
    surah = surah_match.group(1).strip() if surah_match else None
    
    # Extract verse/phrase using the 'قوله تعالى' pattern
    verse_match = re.search(r'قوله تعالى\s+"([^"]+)', title)
    verse = verse_match.group(1).strip() if verse_match else None
    
    # Clean common suffixes from Surah name
    if surah:
        surah = re.sub(r'[-ـ]\s*الجزء.*$', '', surah).strip()
    verse = verse.split("-")[0]
    surah = surah.split("-")[0]

    return verse,surah
def clean_text(text: str,state:str="before") -> str:
    """Remove technical artifacts and normalize text"""
    text = remove_diacritics(text) # remove diacritics for accurate cleaning
    text = re.sub(r'nindex\.php\?[^\s]*', '', text)
    text = re.sub(r'\[\s*ص:\s*\d+\s*\]', '', text)
    if state == "after":
        for sword in SKIPWORDS:
            text = text.split(sword)[0]
    return re.sub(r'\s+', ' ', text).strip()

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
        if isinstance(element, Tag) and any(element.name == x for x in ["span","a"]):
            limit += float('inf')
            # Clean nested elements and check for name patterns
            for nested in element.find_all(['span', 'a']):
                nested.decompose()
                
            text = element.get_text(' ', strip=True)
            for word in UNPOET: 
                if word in text:
                    continue
            if len(text) == 0:
                return Unknown
            return clean_text(text)
        if limit > 3:
            isdone = True
    return Unknown

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
    else:   return ""
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
    d = clean_text(''.join(reversed(context) if direction == 'before' else ''.join(context)),state="before" if direction == "before" else "after")
    return d

def extract_poetry_data(html_content: str) -> list[dict]:
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    verse, surah_name = extract_quranic_info(soup)
    poems = ['']
    duplist = []
    # Find all poetry containers
    for poem in soup.find_all('p', align='center'):
        poetry_lines = ['']
        poetry:bs4.element.Tag = poem.find('font', color="#800080")
        poems.reverse
        try:
            t =  any(clean_text(poetry.text).strip() == clean_text(x["context_after"]).strip() for x in results)
        except:
            t=False
        if any(remove_diacritics(poetry.text).strip() == remove_diacritics(x.strip()) for x in poems) or t:
            poems.reverse
            continue
        poetrynext = poetry.find_next("font",color="#800080")
        poetry_lines.append(poetry.text)  
        poetry.popTag
        if count_br_between(poetry,poetrynext) < 5:
            poetry_lines.append(poetrynext.text)
            poetrynext.popTag 

        combined_poetry = ''.join(poetry_lines).strip()
        # Extract poet and context
        poet_name = extract_poet(poem)
        context_before = extract_context(poem, 'before')
        context_after = extract_context(poem, 'after')
        
                

        # Poet name fallback logic
        for word in LASTPOET:
            if (clean_text(word) in clean_text(context_before) or clean_text(word) == clean_text(context_before)):
                if poet_name == Unknown and results:
                    poet_name = results[-1]["poet"]
                    
        for word in UnknownIZE:
            if word in context_before:
                poet_name = Unknown
        

        key = poet_name+"__"+clean_text(combined_poetry)+"__"+context_before
        if key not in duplist:
            poems.append(remove_diacritics(combined_poetry))

            results.append({
                'poet': poet_name,
                'poetry': clean_text(combined_poetry),
                'context_before': context_before,
                'context_after': context_after,
                'verse': verse,
                'surah': surah_name
            })
            duplist.append(key)
    
    return results

def write_output(data: list[dict], output_file: str):
    with open(output_file, 'w', encoding='utf-8') as f:
        added = []
        for item in data:
            key = item['poet']+"__"+item['poetry']+"__"+item["context_before"]
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

if __name__ == "__main__":
    try:
        start = int(sys.argv[1])
    except:
        start = 27
    x = start
    for html_content in scrape_islamweb_ayas(start_aya=start, limit=1, delay=0.5):
        data = extract_poetry_data(html_content=html_content)
        added = write_output(data, f"output/poetery_PAGE[{x}].txt")
        print(f"Successfully processed {len(added)} in page {x}")
        x += 1
