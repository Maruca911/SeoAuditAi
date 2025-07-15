from flask import Flask, request, jsonify
import urllib.request
from html.parser import HTMLParser
from collections import Counter
import re
import json
from urllib.parse import urlparse
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

class SEOParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = None
        self.meta_desc = None
        self.headings = {'h1': [], 'h2': [], 'h3': []}
        self.images_without_alt = 0
        self.links = {'internal': 0, 'external': 0, 'broken': []}  # Basic count
        self.content_text = []
        self.schema_found = False
        self.video_embeds = 0
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'title':
            self.current_tag = 'title'
        elif tag == 'meta' and attrs_dict.get('name') == 'description':
            self.meta_desc = attrs_dict.get('content')
        elif tag in ['h1', 'h2', 'h3']:
            self.current_tag = tag
        elif tag == 'img':
            if 'alt' not in attrs_dict or not attrs_dict['alt'].strip():
                self.images_without_alt += 1
        elif tag == 'a':
            href = attrs_dict.get('href')
            if href:
                if href.startswith('http'):
                    self.links['external'] += 1
                else:
                    self.links['internal'] += 1
        elif tag == 'script' and attrs_dict.get('type') == 'application/ld+json':
            self.schema_found = True
        elif tag == 'video' or (tag == 'iframe' and 'youtube' in attrs_dict.get('src', '').lower()):
            self.video_embeds += 1

    def handle_data(self, data):
        if self.current_tag == 'title':
            self.title = data.strip()
        elif self.current_tag in ['h1', 'h2', 'h3']:
            self.headings[self.current_tag].append(data.strip())
        else:
            cleaned = data.strip()
            if cleaned:
                self.content_text.append(cleaned)

    def handle_endtag(self, tag):
        self.current_tag = None

def fetch_page(url):
    try:
        with urllib.request.urlopen(url) as response:
            if response.code != 200:
                return None, f"HTTP Error {response.code}"
            html = response.read().decode('utf-8')
            return html, None
    except Exception as e:
        return None, str(e)

def calculate_keyword_density(text):
    words = re.findall(r'\w+', text.lower())
    if not words:
        return {}
    counter = Counter(words)
    total = len(words)
    return {word: count / total * 100 for word, count in counter.most_common(10)}

def check_https(url):
    return urlparse(url).scheme == 'https'

def check_mobile_friendly(html):
    return 'name="viewport"' in html

def check_readability(text):
    words = len(re.findall(r'\w+', text))
    sentences = len(re.split(r'[.!?]', text))
    syllables = sum(len(re.findall(r'[aeiouy]+', word, re.I)) for word in text.split())
    if words == 0 or sentences == 0:
        return 0
    asl = words / sentences
    asw = syllables / words
    return 206.835 - 1.015 * asl - 84.6 * asw

def check_voice_search(text):
    question_words = ['who', 'what', 'where', 'when', 'why', 'how']
    questions = sum(1 for sentence in re.split(r'[.!?]', text) if any(sentence.lower().startswith(word) for word in question_words))
    return questions > 0, questions

def check_ai_overview_potential(html):
    return 'faq' in html.lower() or 'summary' in html.lower()

def check_backlink_toxicity(links):
    return links['external'] > 10

def generate_content_suggestions(keywords, title, meta, headings, issues):
    suggestions = []
    priorities = []
    if not title:
        suggestions.append("Add a title tag with primary keyword.")
        priorities.append("High impact: Improves click-through rates by up to 30%.")
    elif len(title) > 60:
        suggestions.append("Shorten title to under 60 chars.")
        priorities.append("Medium impact: Prevents truncation in search results.")
    if not meta:
        suggestions.append("Add meta description with keywords.")
        priorities.append("High impact: Boosts CTR by 20-40%.")
    if not headings['h1']:
        suggestions.append("Add at least one H1 heading.")
        priorities.append("High impact: Enhances on-page structure for crawlers.")
    primary_kw = max(keywords, key=keywords.get) if keywords else ''
    suggestions.append(f"Incorporate keyword '{primary_kw}' more naturally in content.")
    priorities.append("Medium impact: Improves keyword relevance.")
    if 'images_without_alt' in issues:
        suggestions.append("Add alt text to all images with descriptive keywords.")
        priorities.append("High impact: Improves accessibility and image search rankings.")
    # Sort by assumed impact
    combined = sorted(zip(priorities, suggestions), key=lambda x: 'High' in x[0], reverse=True)
    return [s for _, s in combined], [p for p, _ in combined]

def calculate_health_score(issues):
    total_checks = 10
    errors = len(issues.get('critical', [])) * 3 + len(issues.get('warning', [])) * 1
    score = max(0, 100 - errors * 5)
    return score

def generate_diagram(issues):
    categories = ['Critical', 'Warning', 'Info']
    counts = [len(issues.get('critical', [])), len(issues.get('warning', [])), len(issues.get('info', []))]
    fig, ax = plt.subplots()
    ax.pie(counts, labels=categories, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return f"data:image/png;base64,{img_base64}"

def generate_report(results):
    return json.dumps(results, indent=4)

def analyze_site(url, is_competitor=False):
    html, error = fetch_page(url)
    if error:
        return None, error
    parser = SEOParser()
    parser.feed(html)
    content = ' '.join(parser.content_text)
    keywords = calculate_keyword_density(content)
    https = check_https(url)
    mobile = check_mobile_friendly(html)
    readability = check_readability(content)
    voice_ready, questions = check_voice_search(content)
    ai_potential = check_ai_overview_potential(html)
    backlink_toxic = check_backlink_toxicity(parser.links)
    issues = {'critical': [], 'warning': [], 'info': []}
    if not https:
        issues['critical'].append('Site not using HTTPS')
    if not mobile:
        issues['warning'].append('No viewport meta for mobile')
    if parser.images_without_alt > 0:
        issues['warning'].append(f'{parser.images_without_alt} images without alt text')
    if not parser.schema_found:
        issues['info'].append('No schema markup found')
    if parser.video_embeds == 0:
        issues['info'].append('No video content detected')
    if readability < 60:
        issues['warning'].append('Content readability low')
    if not voice_ready:
        issues['info'].append('No question-based content for voice search')
    if not ai_potential:
        issues['info'].append('Limited potential for AI overviews')
    if backlink_toxic:
        issues['warning'].append('Potential toxic backlinks (too many externals)')
    score = calculate_health_score(issues)
    content_sugs, priorities = generate_content_suggestions(keywords, parser.title, parser.meta_desc, parser.headings, issues)
    diagram = generate_diagram(issues) if not is_competitor else None  # Only for main site
    result = {
        'title': parser.title,
        'meta_description': parser.meta_desc,
        'headings': parser.headings,
        'keyword_density': keywords,
        'links': parser.links,
        'images_without_alt': parser.images_without_alt,
        'schema_found': parser.schema_found,
        'video_embeds': parser.video_embeds,
        'https': https,
        'mobile_friendly': mobile,
        'readability_score': readability,
        'voice_search_ready': voice_ready,
        'questions_count': questions,
        'ai_overview_potential': ai_potential,
        'backlink_toxicity_risk': backlink_toxic,
        'issues': issues,
        'health_score': score,
        'content_suggestions': content_sugs,
        'suggestion_priorities': priorities,
    }
    if diagram:
        result['issues_diagram'] = diagram
    return result, None

@app.route('/audit', methods=['POST'])
def audit():
    data = request.json
    url = data.get('url')
    competitor_url = data.get('competitor_url')
    if not url:
        return jsonify({'error': 'URL required'}), 400

    main_result, main_error = analyze_site(url)
    if main_error:
        return jsonify({'error': main_error}), 500

    competitor_result = None
    if competitor_url:
        competitor_result, comp_error = analyze_site(competitor_url, is_competitor=True)
        if comp_error:
            main_result['competitor_error'] = comp_error
        else:
            # Simple comparison
            comp = {
                'health_score_diff': main_result['health_score'] - competitor_result['health_score'],
                'keyword_overlap': list(set(main_result['keyword_density'].keys()) & set(competitor_result['keyword_density'].keys())),
                'suggestions': []
            }
            if comp['health_score_diff'] < 0:
                comp['suggestions'].append("Your score is lower; focus on matching competitor's strong areas like headings.")
            main_result['competitor_analysis'] = comp
            main_result['competitor_details'] = competitor_result

    main_result['url'] = url
    main_result['report'] = generate_report(main_result)
    main_result['quick_fixes'] = [
        {"fix": "Optimize meta descriptions and titles", "price": 4.99, "impact": "Immediate CTR boost"},
        {"fix": "Add alt text to images", "price": 4.99, "impact": "Better image SEO"},
        {"fix": "Improve H1/H2 structure", "price": 4.99, "impact": "Enhanced on-page ranking"}
    ]  # Simulate buy option

    return jsonify(main_result)

if __name__ == '__main__':
    app.run(debug=True)
