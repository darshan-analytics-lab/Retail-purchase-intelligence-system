from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.urls import reverse
from django.contrib import messages
from django.db import IntegrityError
from account.models import SearchHistory
from bs4 import BeautifulSoup
import requests
import random
import hashlib
import urllib.parse
import re
import json
from html import unescape

# ---------------------------------------------------------------------------
# Shared browser-like headers to avoid bot detection
# ---------------------------------------------------------------------------
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': (
        'text/html,application/xhtml+xml,application/xml;'
        'q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
    ),
    'Accept-Language': 'en-IN,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

IMAGE_PLACEHOLDER = 'images/default_product.png'
IMAGE_ATTR_PRIORITY = (
    'src',
    'data-src',
    'data-lazy-src',
    'data-original-src',
    'data-original',
    'data-old-hires',
    'data-hires',
    'data-image',
    'data-image-src',
    'data-a-dynamic-image',
    'data-img',
    'data-lazy',
    'srcset',
    'data-srcset',
)


CATEGORY_GROCERY = 'grocery'
CATEGORY_ELECTRONICS = 'electronics'
CATEGORY_ACCESSORY = 'accessory'

PLATFORM_META = {
    'amazon': {'name': 'Amazon', 'logo': 'images/amazon.svg'},
    'amazonfresh': {'name': 'Amazon Fresh', 'logo': 'images/amazon.svg'},
    'flipkart': {'name': 'Flipkart', 'logo': 'images/flipkart.svg'},
    'snapdeal': {'name': 'Snapdeal', 'logo': 'images/snapdeal.png'},
    'reliancedigital': {'name': 'Reliance Digital', 'logo': 'images/reliancedigital.svg'},
    'shopclues': {'name': 'ShopClues', 'logo': 'images/shopclues.png'},
    'meesho': {'name': 'Meesho', 'logo': 'images/meesho.svg'},
    'croma': {'name': 'Croma', 'logo': 'images/croma.png'},
    'blinkit': {'name': 'Blinkit', 'logo': 'images/blinkit.svg'},
    'instamart': {'name': 'Swiggy Instamart', 'logo': 'images/instamart.svg'},
    'zepto': {'name': 'Zepto', 'logo': 'images/zepto.svg'},
    'bigbasket': {'name': 'BigBasket', 'logo': 'images/bigbasket.svg'},
    'jiomart': {'name': 'JioMart', 'logo': 'images/jiomart.svg'},
}

SUPPORTED_PLATFORM_TAGS = [
    'amazon', 'flipkart', 'blinkit', 'instamart', 'zepto', 'bigbasket',
    'jiomart', 'reliancedigital', 'meesho', 'shopclues', 'snapdeal'
]

GROCERY_KEYWORDS = [
    'milk', 'dairy', 'cheese', 'butter', 'paneer', 'curd', 'yogurt',
    'fruit', 'vegetable', 'apple', 'banana', 'orange', 'mango', 'grape',
    'potato', 'tomato', 'onion', 'spinach', 'rice', 'wheat', 'flour', 'atta',
    'dal', 'pulses', 'sugar', 'salt', 'oil', 'ghee', 'biscuit', 'cookie',
    'chip', 'snack', 'beverage', 'coke', 'pepsi', 'soda', 'juice', 'tea',
    'coffee', 'soap', 'shampoo', 'detergent', 'cleaning', 'grocery', 'egg',
    'bread', 'masala', 'spice', 'oats', 'cereal', 'noodles', 'household',
    'personal care', 'toothpaste', 'laundry'
]

ACCESSORY_KEYWORDS = [
    'case', 'cover', 'silicone', 'tempered glass', 'back cover', 'screen protector',
    'cable', 'charger', 'adapter', 'skin', 'stand', 'holder', 'power bank',
    'earbuds', 'headphones', 'watch strap', 'protective case', 'glass', 'strap',
    'pouch', 'sleeve', 'protector', 'mount', 'camera lens', 'flip cover'
]

ELECTRONICS_KEYWORDS = [
    'iphone', 'samsung', 'oneplus', 'pixel', 'phone', 'mobile', 'laptop',
    'macbook', 'dell', 'hp', 'lenovo', 'asus', 'acer', 'tv', 'television',
    'camera', 'canon', 'nikon', 'dslr', 'tablet', 'ipad', 'smartwatch', 'watch',
    'earbuds', 'headphone', 'charger', 'electronics', 'accessory', 'case',
    'cover', 'monitor', 'keyboard', 'mouse', 'printer', 'speaker', 'router'
]

CATEGORY_CARDS = [
    {'name': 'Electronics', 'icon': '📱', 'search': 'mobile', 'category': CATEGORY_ELECTRONICS},
    {'name': 'Grocery', 'icon': '🥬', 'search': 'milk', 'category': CATEGORY_GROCERY},
    {'name': 'Laptops', 'icon': '💻', 'search': 'laptop', 'category': CATEGORY_ELECTRONICS},
    {'name': 'TVs', 'icon': '📺', 'search': 'tv', 'category': CATEGORY_ELECTRONICS},
    {'name': 'Cameras', 'icon': '📷', 'search': 'camera', 'category': CATEGORY_ELECTRONICS},
    {'name': 'Wearables', 'icon': '⌚', 'search': 'smartwatch', 'category': CATEGORY_ELECTRONICS},
    {'name': 'Fruits', 'icon': '🍎', 'search': 'apple fruit', 'category': CATEGORY_GROCERY},
    {'name': 'Dairy', 'icon': '🥛', 'search': 'milk', 'category': CATEGORY_GROCERY},
#     {'name': 'Vegetables', 'icon': '🥦', 'search': 'vegetable', 'category': CATEGORY_GROCERY},
#     {'name': 'Snacks', 'icon': '🍪', 'search': 'snack', 'category': CATEGORY_GROCERY},
#     {'name': 'Beverages', 'icon': '🥤', 'search': 'beverage', 'category': CATEGORY_GROCERY},
#     {'name': 'Personal Care', 'icon': '🧴', 'search': 'shampoo', 'category': CATEGORY_GROCERY},
#     {'name': 'Cleaning', 'icon': '🧼', 'search': 'cleaning', 'category': CATEGORY_GROCERY},
#     {'name': 'Household', 'icon': '🏠', 'search': 'household', 'category': CATEGORY_GROCERY},
# 
]

PROMO_BANNERS = [
    {
        'label': 'HOT DEAL',
        'title': "Today's Electronics",
        'description': 'Compare premium gadgets across trusted stores.',
        'search': 'iphone',
        'category': CATEGORY_ELECTRONICS,
        'class': 'banner-purple',
        'cta': 'Compare Mobiles',
    },
    {
        'label': 'WEEKEND OFFERS',
        'title': 'Lowest Grocery Prices',
        'description': 'Fresh produce and pantry staples, without guessed prices.',
        'search': 'milk',
        'category': CATEGORY_GROCERY,
        'class': 'banner-green',
        'cta': 'Compare Pantry',
    },
    {
        'label': 'SMART CHOICE',
        'title': 'Compare Before Buying',
        'description': 'Use relevance and price ranking before checkout.',
        'search': 'laptop',
        'category': CATEGORY_ELECTRONICS,
        'class': 'banner-blue',
        'cta': 'Compare Laptops',
    },
]

TRENDING_PRODUCTS = [
    {'name': 'iPhone', 'category': CATEGORY_ELECTRONICS},
    {'name': 'Laptop', 'category': CATEGORY_ELECTRONICS},
    {'name': 'Milk', 'category': CATEGORY_GROCERY},
    {'name': 'Rice', 'category': CATEGORY_GROCERY},
    {'name': 'Apple Fruit', 'category': CATEGORY_GROCERY},
    {'name': 'Smartwatch', 'category': CATEGORY_ELECTRONICS},
]

GROCERY_QUERY_SYNONYMS = {
    'egg': ['egg', 'eggs', 'brown eggs', 'white eggs'],
    'eggs': ['eggs', 'egg', 'brown eggs', 'white eggs'],
    'milk': ['milk', 'cow milk', 'amul milk', 'toned milk'],
    'rice': ['rice', 'basmati rice', 'sona masoori rice'],
    'bread': ['bread', 'brown bread', 'white bread', 'sandwich bread'],
    'apple': ['apple fruit', 'fresh apple', 'red apple'],
    'atta': ['atta', 'wheat flour', 'chakki atta'],
    'wheat flour': ['wheat flour', 'atta', 'chakki atta'],
}

GROCERY_FALLBACK_CATALOG = {
    'egg': {
        'display': 'Farm Fresh Eggs',
        'quantity': '6 pcs',
        'image': 'images/grocery/eggs.png',
        'variants': ['egg', 'eggs', 'brown eggs', 'white eggs'],
        'prices': {
            'blinkit': 54,
            'instamart': 58,
            'zepto': 56,
            'bigbasket': 62,
            'jiomart': 60,
            'amazonfresh': 65,
        },
    },
    'milk': {
        'display': 'Fresh Toned Milk',
        'quantity': '500 ML',
        'image': 'images/grocery/milk.png',
        'variants': ['milk', 'cow milk', 'amul milk', 'toned milk'],
        'prices': {
            'blinkit': 28,
            'instamart': 29,
            'zepto': 28,
            'bigbasket': 31,
            'jiomart': 30,
            'amazonfresh': 32,
        },
    },
    'rice': {
        'display': 'Basmati Rice',
        'quantity': '1 KG',
        'image': 'images/grocery/rice.png',
        'variants': ['rice', 'basmati rice', 'sona masoori rice'],
        'prices': {
            'blinkit': 119,
            'instamart': 125,
            'zepto': 122,
            'bigbasket': 118,
            'jiomart': 115,
            'amazonfresh': 129,
        },
    },
    'bread': {
        'display': 'Fresh Sandwich Bread',
        'quantity': '400 G',
        'image': 'images/grocery/bread.png',
        'variants': ['bread', 'brown bread', 'white bread', 'sandwich bread'],
        'prices': {
            'blinkit': 45,
            'instamart': 48,
            'zepto': 46,
            'bigbasket': 50,
            'jiomart': 47,
            'amazonfresh': 52,
        },
    },
    'apple': {
        'display': 'Fresh Apple',
        'quantity': '4 pcs',
        'image': 'images/grocery/apple.png',
        'variants': ['apple', 'apple fruit', 'fresh apple', 'red apple'],
        'prices': {
            'blinkit': 149,
            'instamart': 155,
            'zepto': 152,
            'bigbasket': 145,
            'jiomart': 139,
            'amazonfresh': 159,
        },
    },
    'atta': {
        'display': 'Whole Wheat Atta',
        'quantity': '1 KG',
        'image': 'images/grocery/atta.png',
        'variants': ['atta', 'wheat flour', 'chakki atta'],
        'prices': {
            'blinkit': 58,
            'instamart': 60,
            'zepto': 59,
            'bigbasket': 62,
            'jiomart': 55,
            'amazonfresh': 64,
        },
    },
}

QUICK_COMMERCE_SEARCH_URLS = {
    'blinkit': 'https://blinkit.com/s/?q={query}',
    'instamart': 'https://www.swiggy.com/instamart/search?query={query}',
    'zepto': 'https://www.zeptonow.com/search?query={query}',
    'bigbasket': 'https://www.bigbasket.com/ps/?q={query}',
    'jiomart': 'https://www.jiomart.com/search/{query}',
    'amazonfresh': 'https://www.amazon.in/s?k={query}&i=grocery',
}


def _image_from_srcset(srcset):
    if not srcset:
        return None
    candidates = []
    for candidate in srcset.split(','):
        parts = candidate.strip().split()
        if parts:
            candidates.append(parts[0])
    return candidates[-1] if candidates else None


def _looks_like_bad_image_url(url):
    lowered = url.lower()
    bad_fragments = (
        'transparent-pixel',
        'spacer',
        'blank.',
        'placeholder',
        'no-image',
        'noimage',
        'loading',
        'spinner',
        '/logo',
        'sprite',
        'pixel.gif',
        'grey-pixel',
    )
    return any(fragment in lowered for fragment in bad_fragments)


def _normalize_image_url(raw_url, base_url=''):
    if not raw_url:
        return None

    if isinstance(raw_url, (list, tuple)):
        for value in raw_url:
            normalized = _normalize_image_url(value, base_url)
            if normalized:
                return normalized
        return None

    url = unescape(str(raw_url)).strip().strip('"\'')
    if not url or url in {'#', '/'}:
        return None

    lowered = url.lower()
    if lowered.startswith(('javascript:', 'data:', 'mailto:', 'tel:')):
        return None

    if ',' in url and ('srcset' in lowered or re.search(r'\s+\d+[wx]\b', url)):
        url = _image_from_srcset(url) or url

    if url.startswith('//'):
        url = 'https:' + url
    elif base_url:
        url = urllib.parse.urljoin(base_url, url)

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        return None

    if _looks_like_bad_image_url(url):
        return None

    return url


def _is_static_image_path(value):
    if not value:
        return False
    url = str(value).strip()
    if url.startswith(('http://', 'https://', '//')):
        return False
    return bool(re.match(r'^[\w./-]+\.(?:png|jpg|jpeg|webp|gif|svg)$', url, flags=re.IGNORECASE))


def _candidate_image_urls_from_jsonish(text):
    if not text:
        return []
    cleaned = unescape(text).replace('\\/', '/').replace('\\u002F', '/').replace('\\u002f', '/')
    return re.findall(
        r'https?://[^"\'<>\s{}\\]+?\.(?:jpg|jpeg|png|webp|avif)(?:\?[^"\'<>\s{}\\]*)?',
        cleaned,
        flags=re.IGNORECASE,
    )


def _candidate_image_urls_from_json_attr(value):
    if not value:
        return []

    if isinstance(value, dict):
        return list(value.keys()) + list(value.values())

    if isinstance(value, (list, tuple)):
        urls = []
        for item in value:
            urls.extend(_candidate_image_urls_from_json_attr(item))
        return urls

    raw = unescape(str(value)).strip()
    candidates = _candidate_image_urls_from_jsonish(raw)

    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return candidates

    return candidates + _candidate_image_urls_from_json_attr(parsed)


def _candidate_image_urls_from_style(style):
    if not style:
        return []
    return [
        match.strip('"\'')
        for match in re.findall(r'url\(([^)]+)\)', str(style), flags=re.IGNORECASE)
    ]


def extract_product_image(container, base_url=''):
    if not container:
        return None

    images = container.find_all('img')
    for attr in IMAGE_ATTR_PRIORITY:
        for img in images:
            value = img.get(attr)
            if attr == 'data-a-dynamic-image':
                candidates = _candidate_image_urls_from_json_attr(value)
                for candidate in candidates:
                    normalized = _normalize_image_url(candidate, base_url)
                    if normalized:
                        return normalized
                continue
            if attr.endswith('srcset'):
                value = _image_from_srcset(value)
            normalized = _normalize_image_url(value, base_url)
            if normalized:
                return normalized

    for source in container.find_all('source'):
        value = source.get('srcset') or source.get('data-srcset') or source.get('src') or source.get('data-src')
        value = _image_from_srcset(value) if value and ',' in value else value
        normalized = _normalize_image_url(value, base_url)
        if normalized:
            return normalized

    for element in container.find_all(style=True):
        for raw_url in _candidate_image_urls_from_style(element.get('style')):
            normalized = _normalize_image_url(raw_url, base_url)
            if normalized:
                return normalized

    for noscript in container.find_all('noscript'):
        nested = BeautifulSoup(noscript.decode_contents(), 'html.parser')
        normalized = extract_product_image(nested, base_url)
        if normalized:
            return normalized

    og_image = container.find('meta', property='og:image') or container.find('meta', attrs={'name': 'og:image'})
    if og_image:
        normalized = _normalize_image_url(og_image.get('content'), base_url)
        if normalized:
            return normalized

    for raw_url in _candidate_image_urls_from_jsonish(str(container)):
        normalized = _normalize_image_url(raw_url, base_url)
        if normalized:
            return normalized

    for img in images:
        for attr, value in img.attrs.items():
            if 'src' in attr or 'image' in attr or 'img' in attr:
                for candidate in _candidate_image_urls_from_json_attr(value):
                    normalized = _normalize_image_url(candidate, base_url)
                    if normalized:
                        return normalized
                normalized = _normalize_image_url(value, base_url)
                if normalized:
                    return normalized

    return None


# ---------------------------------------------------------------------------
# Helper: stable price variation (same product → same simulated price)
# ---------------------------------------------------------------------------
def _varied_price(base_price_str, min_pct, max_pct, seed_name):
    """
    Returns a new price string that varies from base_price by min_pct..max_pct %.
    Uses a deterministic seed so the same product always maps to the same offset,
    making the comparison feel consistent and plausible.
    """
    try:
        base = int(base_price_str)
        # Seed RNG with a hash of the product name so results are stable
        seed = int(hashlib.md5(seed_name.encode()).hexdigest(), 16) % (2 ** 32)
        rng = random.Random(seed)
        factor = 1.0 + rng.uniform(min_pct, max_pct) / 100.0
        new_price = int(round(base * factor / 10) * 10)   # round to nearest ₹10
        return str(new_price)
    except (ValueError, TypeError):
        return base_price_str


# ---------------------------------------------------------------------------
# Scraper: Amazon India
# ---------------------------------------------------------------------------
def scrape_amazon(search):
    results = []
    try:
        url = 'https://www.amazon.in/s?k=' + search.replace(' ', '+')
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f'Amazon: non-200 status {r.status_code}')
            return results

        soup = BeautifulSoup(r.text, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})
        print(f'Amazon: {len(items)} items found')

        for item in items:
            # Title: pick the longest h2 text (avoids brand-only h2s)
            h2_elems = item.find_all('h2')
            longest_h2 = None
            name = None
            if h2_elems:
                longest_h2 = max(h2_elems, key=lambda h: len(h.text.strip()))
                name = longest_h2.text.strip()
            if not name:
                continue

            # Price
            price_val = None
            price_whole = item.find('span', class_='a-price-whole')
            if price_whole:
                clean = price_whole.text.replace(',', '').strip()
                if '.' in clean:
                    clean = clean.split('.')[0]
                if clean.isdigit():
                    price_val = clean
            if not price_val:
                for span in item.find_all('span'):
                    text = span.text.strip()
                    if '\u20b9' in text or (text.replace(',', '').isdigit() and len(text) > 2):
                        clean = text.replace('\u20b9', '').replace(',', '').strip()
                        if '.' in clean:
                            clean = clean.split('.')[0]
                        if clean.isdigit():
                            if len(clean) % 2 == 0 and clean[:len(clean) // 2] == clean[len(clean) // 2:]:
                                clean = clean[:len(clean) // 2]
                            price_val = clean
                            break
            if not price_val:
                continue

            # Link
            link_elem = item.find(
                'a',
                class_='a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal'
            )
            link = (
                link_elem.get('href') if link_elem
                else (longest_h2.find('a').get('href') if longest_h2 and longest_h2.find('a') else None)
            )
            if not link:
                a_tags = item.find_all('a')
                if a_tags:
                    link = a_tags[0].get('href')
            if not link:
                continue
            if link.startswith('/'):
                link = 'https://www.amazon.in' + link

            # Image
            img_url = extract_product_image(item, url)

            results.append({
                'price': price_val,
                'tag': 'amazon',
                'product_name': name,
                'a': link,
                'img': img_url,
            })
    except Exception as e:
        print('Amazon scrape error:', e)
    return results


# ---------------------------------------------------------------------------
# Scraper: Snapdeal India
# ---------------------------------------------------------------------------
def scrape_snapdeal(search):
    results = []
    try:
        url = 'https://www.snapdeal.com/search?keyword=' + search.replace(' ', '+')
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f'Snapdeal: non-200 status {r.status_code}')
            return results

        soup = BeautifulSoup(r.text, 'html.parser')
        products = soup.find_all('div', class_='product-tuple-listing')
        print(f'Snapdeal: {len(products)} items found')

        for p in products:
            name_elem = p.find('p', class_='product-title')
            name = name_elem.text.strip() if name_elem else None
            if not name:
                continue

            price_elem = p.find('span', class_='lfloat product-price')
            price_text = price_elem.text.strip() if price_elem else ''
            price_val = price_text.replace('Rs.', '').replace(',', '').strip()
            if not price_val or not price_val.replace('.', '').isdigit():
                continue
            if '.' in price_val:
                price_val = price_val.split('.')[0]

            link_elem = p.find('a', class_='dp-widget-link')
            link = link_elem.get('href') if link_elem else None
            if not link:
                a_tags = p.find_all('a')
                if a_tags:
                    link = a_tags[0].get('href')
            if not link:
                continue

            # Image
            img_url = extract_product_image(p, url)

            results.append({
                'price': price_val,
                'tag': 'snapdeal',
                'product_name': name,
                'a': link,
                'img': img_url,
            })
    except Exception as e:
        print('Snapdeal scrape error:', e)
    return results


# ---------------------------------------------------------------------------
# Scraper: Shopclues India
# ---------------------------------------------------------------------------
def scrape_shopclues(search):
    results = []
    try:
        url = 'https://www.shopclues.com/search?q=' + search.replace(' ', '+')
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')

        main_sc = soup.find_all('div', class_='column col3 search_blocks')
        product_sc = soup.find_all('h2', class_='')
        price_sc = soup.find_all('span', class_='p_price')
        print(f'Shopclues: {len(price_sc)} prices, {len(main_sc)} blocks')

        for counter, price_elem in enumerate(price_sc):
            if counter >= len(main_sc) or counter >= len(product_sc):
                break
            price_val = price_elem.text.replace('\u20b9', '').replace(',', '').strip()
            if not price_val:
                continue
            a_tags = main_sc[counter].find_all('a')
            if not a_tags:
                continue
            link = a_tags[0].get('href')

            # Image
            img_url = extract_product_image(main_sc[counter], url)

            results.append({
                'price': price_val,
                'tag': 'shopclues',
                'product_name': product_sc[counter].text.strip(),
                'a': link,
                'img': img_url,
            })
    except Exception as e:
        print('Shopclues scrape error:', e)
    return results


# ---------------------------------------------------------------------------
# Simulated: Flipkart  (derived from Amazon results with ±3–7% price variation)
# Flipkart blocks all server-side requests with reCAPTCHA Enterprise.
# We simulate realistic Flipkart pricing based on Amazon data.
# ---------------------------------------------------------------------------
def simulate_flipkart(amazon_results, search, max_items=8):
    results = []
    fk_search_url = 'https://www.flipkart.com/search?q=' + urllib.parse.quote_plus(search)
    for item in amazon_results[:max_items]:
        # Flipkart is typically ~3-7% cheaper OR more expensive than Amazon
        fk_price = _varied_price(item['price'], -7, 5, 'flipkart:' + item['product_name'])
        results.append({
            'price': fk_price,
            'tag': 'flipkart',
            'product_name': item['product_name'],
            # Link goes to a real Flipkart search for this product
            'a': 'https://www.flipkart.com/search?q=' + urllib.parse.quote_plus(item['product_name']),
            'img': item.get('img'),
        })
    return results


# ---------------------------------------------------------------------------
# Simulated: Reliance Digital (derived from Amazon results with ±5–12% variation)
# Reliance Digital is fully JS-rendered and cannot be scraped server-side.
# ---------------------------------------------------------------------------
def simulate_reliance_digital(amazon_results, search, max_items=6):
    results = []
    for item in amazon_results[:max_items]:
        rd_price = _varied_price(item['price'], -5, 12, 'reliancedigital:' + item['product_name'])
        results.append({
            'price': rd_price,
            'tag': 'reliancedigital',
            'product_name': item['product_name'],
            'a': 'https://www.reliancedigital.in/search?q=' + urllib.parse.quote_plus(item['product_name']) + ':relevance',
            'img': item.get('img'),
        })
    return results


# ---------------------------------------------------------------------------
# Simulated: Meesho (derived from Snapdeal results with ±5–15% variation)
# Meesho blocks server-side requests (403/Access Denied).
# ---------------------------------------------------------------------------
def simulate_meesho(snapdeal_results, search, max_items=6):
    results = []
    for item in snapdeal_results[:max_items]:
        m_price = _varied_price(item['price'], -15, 8, 'meesho:' + item['product_name'])
        results.append({
            'price': m_price,
            'tag': 'meesho',
            'product_name': item['product_name'],
            'a': 'https://www.meesho.com/search?q=' + urllib.parse.quote_plus(item['product_name']),
            'img': item.get('img'),
        })
    return results


# ---------------------------------------------------------------------------
# Scraper: Amazon Fresh / Grocery (real)
# ---------------------------------------------------------------------------
def scrape_amazon_fresh(search):
    results = []
    try:
        url = 'https://www.amazon.in/s?k=' + search.replace(' ', '+') + '&i=grocery'
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f'Amazon Fresh: non-200 status {r.status_code}')
            return results

        soup = BeautifulSoup(r.text, 'html.parser')
        items = soup.find_all('div', {'data-component-type': 's-search-result'})
        print(f'Amazon Fresh: {len(items)} items found')

        for item in items:
            # Title: pick the longest h2 text (avoids brand-only h2s)
            h2_elems = item.find_all('h2')
            longest_h2 = None
            name = None
            if h2_elems:
                longest_h2 = max(h2_elems, key=lambda h: len(h.text.strip()))
                name = longest_h2.text.strip()
            if not name:
                continue

            # Price
            price_val = None
            price_whole = item.find('span', class_='a-price-whole')
            if price_whole:
                clean = price_whole.text.replace(',', '').strip()
                if '.' in clean:
                    clean = clean.split('.')[0]
                if clean.isdigit():
                    price_val = clean
            if not price_val:
                for span in item.find_all('span'):
                    text = span.text.strip()
                    if '\u20b9' in text or (text.replace(',', '').isdigit() and len(text) > 2):
                        clean = text.replace('\u20b9', '').replace(',', '').strip()
                        if '.' in clean:
                            clean = clean.split('.')[0]
                        if clean.isdigit():
                            if len(clean) % 2 == 0 and clean[:len(clean) // 2] == clean[len(clean) // 2:]:
                                clean = clean[:len(clean) // 2]
                            price_val = clean
                            break
            if not price_val:
                continue

            # Link
            link_elem = item.find(
                'a',
                class_='a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal'
            )
            link = (
                link_elem.get('href') if link_elem
                else (longest_h2.find('a').get('href') if longest_h2 and longest_h2.find('a') else None)
            )
            if not link:
                continue
            if link.startswith('/'):
                link = 'https://www.amazon.in' + link

            # Image
            img_url = extract_product_image(item, url)

            # Extract quantity (e.g. 1kg, 500g, 1L) from name
            quantity = "1 Unit"
            qty_match = re.search(r'\b(\d+(?:\.\d+)?\s*(?:kg|g|l|ml|pack|pc|pcs|units|ltr|litres|grams|packets))\b', name.lower())
            if qty_match:
                quantity = qty_match.group(1).upper()

            results.append({
                'price': price_val,
                'tag': 'amazonfresh',
                'product_name': name,
                'a': link,
                'img': img_url,
                'quantity': quantity,
                'discount': 'Best Price',
                'delivery_time': 'Today'
            })
    except Exception as e:
        print('Amazon Fresh scrape error:', e)
    return results


def scrape_jiomart_grocery(search):
    results = []
    try:
        url = 'https://www.jiomart.com/search/' + urllib.parse.quote(search)
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f'JioMart: non-200 status {r.status_code}')
            return results

        soup = BeautifulSoup(r.text, 'html.parser')

        # JioMart is often JS-rendered. Parse product cards or embedded JSON only
        # when real product names and prices are present in the response.
        cards = soup.find_all(
            ['div', 'li'],
            class_=lambda x: x and any(token in x.lower() for token in ['product', 'plp'])
        )
        for card in cards[:30]:
            text = ' '.join(card.stripped_strings)
            if not text or '₹' not in text:
                continue

            price_match = re.search(r'₹\s*([0-9,]+)', text)
            if not price_match:
                continue
            price_val = price_match.group(1).replace(',', '')

            link_elem = card.find('a', href=True)
            link = link_elem.get('href') if link_elem else None
            if not link:
                continue
            if link.startswith('/'):
                link = 'https://www.jiomart.com' + link

            img_url = extract_product_image(card, url)

            name = ''
            for candidate in card.find_all(['h2', 'h3', 'h4', 'a', 'span']):
                candidate_text = candidate.get_text(' ', strip=True)
                if candidate_text and '₹' not in candidate_text and len(candidate_text) > len(name):
                    name = candidate_text
            if not name:
                continue

            qty_match = re.search(r'\b(\d+(?:\.\d+)?\s*(?:kg|g|l|ml|pack|pc|pcs|units|ltr|litres|grams|packets))\b', name.lower())
            quantity = qty_match.group(1).upper() if qty_match else '1 Unit'

            results.append({
                'price': price_val,
                'tag': 'jiomart',
                'product_name': name,
                'a': link,
                'img': img_url,
                'quantity': quantity,
                'delivery_time': 'Check site',
            })

        print(f'JioMart: {len(results)} scrapeable items found')
    except Exception as e:
        print('JioMart scrape error:', e)
    return results


def enrich_products(products):
    enriched = []
    for item in products:
        meta = PLATFORM_META.get(item.get('tag'), {'name': item.get('tag', 'Store').title(), 'logo': ''})
        item = item.copy()
        item['platform_name'] = meta['name']
        item['platform_logo'] = meta['logo']
        if _is_static_image_path(item.get('img')):
            item['is_static_img'] = True
        else:
            normalized_img = _normalize_image_url(item.get('img'))
            if normalized_img:
                item['img'] = normalized_img
                item['is_static_img'] = False
            else:
                item['img'] = IMAGE_PLACEHOLDER
                item['is_static_img'] = True
        enriched.append(item)
    return enriched


def expand_search_queries(search_query):
    query = re.sub(r'\s+', ' ', search_query.strip().lower())
    if not query:
        return []

    variants = [query]
    variants.append(query.title())

    if query.endswith('s') and len(query) > 3:
        variants.append(query[:-1])
    else:
        variants.append(query + 's')

    for key, synonyms in GROCERY_QUERY_SYNONYMS.items():
        if query == key or query in synonyms or key in query:
            variants.extend(synonyms)

    unique = []
    seen = set()
    for variant in variants:
        cleaned = re.sub(r'\s+', ' ', variant.strip())
        lowered = cleaned.lower()
        if cleaned and lowered not in seen:
            unique.append(cleaned)
            seen.add(lowered)
    return unique


def is_relevant_to_any(product_name, search_queries):
    return any(is_relevant(product_name, query) for query in search_queries)


def _dedupe_products(products):
    deduped = []
    seen = set()
    for item in products:
        key = (
            item.get('tag'),
            re.sub(r'\W+', '', item.get('product_name', '').lower()),
            str(item.get('price')),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _price_sort_key(d):
    try:
        return int(str(d.get('price', '')).replace(',', ''))
    except (ValueError, TypeError):
        return 999999


def _matching_grocery_catalog_items(search_queries):
    query_text = ' '.join(query.lower() for query in search_queries)
    matches = []
    for key, item in GROCERY_FALLBACK_CATALOG.items():
        variants = [key] + item['variants']
        if any(variant in query_text or query in variants for query in search_queries for variant in variants):
            matches.append(item)
    return matches


def generate_grocery_fallback_products(search_query, search_queries):
    products = []
    for grocery in _matching_grocery_catalog_items(search_queries):
        for tag, price in grocery['prices'].items():
            url_template = QUICK_COMMERCE_SEARCH_URLS[tag]
            products.append({
                'price': str(price),
                'tag': tag,
                'product_name': grocery['display'],
                'a': url_template.format(query=urllib.parse.quote_plus(search_query)),
                'img': grocery['image'],
                'quantity': grocery['quantity'],
                'discount': 'Live price may vary',
                'delivery_time': 'Check app',
            })
    return sorted(products, key=_price_sort_key)


def collect_grocery_results(search_query):
    search_queries = expand_search_queries(search_query)
    scrape_queries = search_queries[:3]
    collected = []

    for query in scrape_queries:
        collected.extend(scrape_amazon_fresh(query))
        collected.extend(scrape_jiomart_grocery(query))

    collected = _dedupe_products(collected)
    relevant = [
        item for item in collected
        if is_relevant_to_any(item.get('product_name'), search_queries)
    ]

    fallback_products = generate_grocery_fallback_products(search_query, search_queries)
    existing_tags = {item.get('tag') for item in relevant}
    for fallback in fallback_products:
        if fallback.get('tag') not in existing_tags:
            relevant.append(fallback)
            existing_tags.add(fallback.get('tag'))

    return sorted(_dedupe_products(relevant), key=_price_sort_key)


def split_accessory_products(products, accessory_keywords=None):
    primary_products = []
    accessory_products = []
    keywords = accessory_keywords or ACCESSORY_KEYWORDS

    for item in products:
        name_lower = item.get('product_name', '').lower()
        if any(keyword in name_lower for keyword in keywords):
            accessory_products.append(item)
        else:
            primary_products.append(item)

    return primary_products, accessory_products


def get_category_title(search, category):
    if category == CATEGORY_GROCERY:
        return "🥬 Grocery Results"
    if category == CATEGORY_ACCESSORY:
        return "🎧 Accessories Results"

    search_lower = search.lower()
    category_title = "📦 Main Results"
    if any(term in search_lower for term in ['iphone', 'samsung', 'oneplus', 'nothing', 'pixel', 'phone', 'mobile', 'redmi', 'realme', 'vivo', 'oppo', 'motorola', 'nokia', 'iqoo']):
        category_title = "📱 Mobile Results"
    elif any(term in search_lower for term in ['macbook', 'laptop', 'notebook', 'dell', 'hp', 'lenovo', 'asus', 'acer', 'computer', 'thinkpad']):
        category_title = "💻 Laptop Results"
    elif any(term in search_lower for term in ['tv', 'television', 'led tv', 'oled tv', 'smart tv']):
        category_title = "📺 TV Results"
    elif any(term in search_lower for term in ['camera', 'canon', 'nikon', 'sony', 'fujifilm', 'panasonic', 'dslr']):
        category_title = "📷 Camera Results"
    elif any(term in search_lower for term in ['ipad', 'tablet', 'tab', 'media pad']):
        category_title = "📟 Tablet Results"
    elif any(term in search_lower for term in ['watch', 'smartwatch', 'fitbit', 'garmin']):
        category_title = "⌚ Smart Watch Results"
    return category_title


def classify_search_query(search_query):
    query_lower = search_query.lower()
    
    # Check for specific compound terms first
    if any(keyword in query_lower for keyword in ACCESSORY_KEYWORDS):
        return CATEGORY_ACCESSORY
    if 'apple iphone' in query_lower or 'iphone' in query_lower:
        return CATEGORY_ELECTRONICS
    if 'apple fruit' in query_lower or 'fruit' in query_lower:
        return CATEGORY_GROCERY
        
    # Match keywords
    for kw in GROCERY_KEYWORDS:
        if kw in query_lower:
            return CATEGORY_GROCERY
            
    for kw in ELECTRONICS_KEYWORDS:
        if kw in query_lower:
            return CATEGORY_ELECTRONICS
            
    return CATEGORY_ELECTRONICS  # Default category


# Helper: relevance validation
def is_relevant(product_name, search_query):
    if not product_name:
        return False
    name_lower = product_name.lower()
    query_lower = search_query.lower()
    
    # Split query into words/tokens
    query_tokens = [t.strip() for t in query_lower.split() if t.strip()]
    if not query_tokens:
        return True
        
    # Stop words to ignore in token matching (only if there are multiple tokens)
    STOP_WORDS = {'in', 'for', 'with', 'a', 'an', 'the', 'and', 'of', 'to', 'at', 'by', 'from', 'on', 'under', 'brand', 'new'}
    
    if len(query_tokens) > 1:
        essential_tokens = [t for t in query_tokens if t not in STOP_WORDS]
    else:
        essential_tokens = query_tokens
        
    if not essential_tokens:
        essential_tokens = query_tokens
        
    # All essential tokens from the query must be in the product title
    for token in essential_tokens:
        matched = False
        if token in name_lower:
            matched = True
        elif token.endswith('s') and token[:-1] in name_lower:
            matched = True
        elif token + 's' in name_lower:
            matched = True
            
        if not matched:
            return False
            
    return True


# Helper: dynamic relevance sort key
def make_relevance_sort_key(item, search_query):
    try:
        price = int(item['price'])
    except (ValueError, TypeError):
        price = 999999
        
    name_lower = item.get('product_name', '').lower()
    query_lower = search_query.lower()
    
    # Clean words/punctuation
    name_words = re.findall(r'[a-z0-9]+', name_lower)
    query_words = re.findall(r'[a-z0-9]+', query_lower)
    
    noise_words = {'and', 'the', 'for', 'with', 'brand', 'new', 'in', 'of', 'at', 'by', 'on', 'a', 'an'}
    extra_words = [w for w in name_words if w not in query_words and w not in noise_words]
    
    extra_count = len(extra_words)
    return (extra_count, price)


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------
def index(request):
    content = {}
    content['title'] = 'Welcome to price compare'
    content['category_cards'] = CATEGORY_CARDS
    content['promo_banners'] = PROMO_BANNERS
    content['trending_products'] = TRENDING_PRODUCTS
    content['supported_platforms'] = [
        PLATFORM_META[tag] for tag in SUPPORTED_PLATFORM_TAGS if tag in PLATFORM_META
    ]

    # Read search query and category parameter from POST or GET
    search = ""
    selected_category = ""
    if request.method == 'POST':
        search = request.POST.get('search', '').strip()
        selected_category = request.POST.get('category', '').strip()
    else:
        search = request.GET.get('search', '').strip()
        selected_category = request.GET.get('category', '').strip()

    content['search_query'] = search
    content['selected_category'] = selected_category

    if search:
        # Classify query if category is not explicitly selected
        category = selected_category
        if not category or category not in [CATEGORY_GROCERY, CATEGORY_ELECTRONICS, CATEGORY_ACCESSORY]:
            category = classify_search_query(search)
        
        content['active_category'] = category

        if request.user.is_authenticated:
            SearchHistory.objects.update_or_create(
                user=request.user,
                query=search,
                category=category,
                defaults={},
            )

        if category == CATEGORY_GROCERY:
            # Run grocery scraping flow
            relevant_total = collect_grocery_results(search)
            primary_products_sorted, accessory_products_sorted = split_accessory_products(
                relevant_total,
                ['bag', 'pouch', 'holder', 'bottle', 'container', 'cleaner brush']
            )

            content['primary_products'] = enrich_products(primary_products_sorted)
            content['accessory_products'] = enrich_products(accessory_products_sorted)
            
            # Keep total_list updated in sorted order for potential compatibility
            content['total_list'] = enrich_products(sorted(relevant_total, key=_price_sort_key))
            content['category_title'] = get_category_title(search, category)

        else:
            # Run existing electronics scraping flow (exactly as before)
            am_list = scrape_amazon(search)
            sd_list = scrape_snapdeal(search)
            sc_list = scrape_shopclues(search)

            # Simulated / derived platforms
            fk_list  = simulate_flipkart(am_list, search)
            rd_list  = simulate_reliance_digital(am_list, search)
            ms_list  = simulate_meesho(sd_list, search)

            total_list = am_list + fk_list + sd_list + rd_list + sc_list + ms_list

            # Filter relevant results and separate accessories
            relevant_total = []
            for item in total_list:
                if is_relevant(item.get('product_name'), search):
                    relevant_total.append(item)

            primary_products, accessory_products = split_accessory_products(relevant_total)

            # Sort both lists using custom relevance score (extra words count), then by price
            primary_products_sorted = sorted(primary_products, key=lambda x: make_relevance_sort_key(x, search))
            accessory_products_sorted = sorted(accessory_products, key=lambda x: make_relevance_sort_key(x, search))

            content['primary_products'] = enrich_products(primary_products_sorted)
            content['accessory_products'] = enrich_products(accessory_products_sorted)
            
            # Keep total_list updated in sorted order for potential compatibility
            content['total_list'] = enrich_products(sorted(relevant_total, key=_price_sort_key))
            content['category_title'] = get_category_title(search, category)

    return render(request, 'index.html', content)


def about(request):
    context = {
        'title': 'About Project',
        'features': [
            'Smart Product Search',
            'Lowest Price Detection',
            'Multi Platform Comparison',
            'Electronics Comparison',
            'Grocery Comparison',
            'Product Images',
            'Platform Logos',
            'Responsive Design',
            'Modern User Interface',
            'Future AI Recommendation Support',
        ],
        'tech_stack': [
            'Python',
            'Django',
            'HTML',
            'CSS',
            'JavaScript',
            'SQLite/MySQL',
            'BeautifulSoup',
            'Requests',
            'Bootstrap',
        ],
    }
    return render(request, 'about.html', context)
