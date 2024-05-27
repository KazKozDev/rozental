from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

def fetch_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return url, response.text
    except requests.RequestException as e:
        print(f"Ошибка при обработке {url}: {e}")
        return url, None

def split_into_sentences(text):
    sentence_endings = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s')
    sentences = sentence_endings.split(text)
    return sentences

def highlight_query(text, query):
    highlighted_text = re.sub(f"({re.escape(query)})", r'✅\1', text, flags=re.IGNORECASE)
    return highlighted_text

def extract_context(text, query):
    sentences = split_into_sentences(text)
    context = []
    for i, sentence in enumerate(sentences):
        if re.search(query, sentence, re.IGNORECASE):
            start = max(0, i - 1)
            end = min(len(sentences), i + 2)
            context_with_highlight = ' '.join([highlight_query(s, query) for s in sentences[start:end)])
            context.append(context_with_highlight)
    return context

def search_site(start_url, query, max_depth=2):
    results = []
    visited_urls = set()
    urls_to_visit = [(start_url, 0)]
    executor = ThreadPoolExecutor(max_workers=10)
    futures = []

    while urls_to_visit or futures:
        while urls_to_visit:
            current_url, depth = urls_to_visit.pop(0)
            if depth > max_depth:
                continue
            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)
            futures.append(executor.submit(fetch_url, current_url))

        for future in as_completed(futures):
            futures.remove(future)
            current_url, text = future.result()
            if not text:
                continue
            soup = BeautifulSoup(text, 'html.parser')
            page_text = soup.get_text()
            context = extract_context(page_text, query)
            if context:
                results.append((current_url, context))
                print(f"Найдено '{query}' на {current_url}")
            for link in soup.find_all('a', href=True):
                url = link['href']
                full_url = urljoin(current_url, url)
                if urlparse(full_url).netloc == urlparse(start_url).netloc:
                    if full_url not in visited_urls:
                        urls_to_visit.append((full_url, depth + 1))
    
    executor.shutdown(wait=True)
    return results

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter is requi
