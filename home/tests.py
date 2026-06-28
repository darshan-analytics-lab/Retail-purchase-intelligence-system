from bs4 import BeautifulSoup
from django.test import SimpleTestCase
from unittest.mock import patch

from home.views import (
    CATEGORY_ACCESSORY,
    CATEGORY_ELECTRONICS,
    CATEGORY_GROCERY,
    IMAGE_PLACEHOLDER,
    classify_search_query,
    collect_grocery_results,
    enrich_products,
    expand_search_queries,
    extract_product_image,
)


class ProductImageExtractionTests(SimpleTestCase):
    def test_extracts_lazy_image_attributes(self):
        soup = BeautifulSoup(
            '<div><img src="#" data-lazy-src="/images/phone.webp"></div>',
            'html.parser',
        )

        self.assertEqual(
            extract_product_image(soup.div, 'https://example.com/search'),
            'https://example.com/images/phone.webp',
        )

    def test_extracts_amazon_dynamic_image_json(self):
        soup = BeautifulSoup(
            '''
            <div>
                <img src="https://example.com/transparent-pixel.gif"
                     data-a-dynamic-image='{"https://cdn.example.com/phone.jpg":[500,500]}'>
            </div>
            ''',
            'html.parser',
        )

        self.assertEqual(
            extract_product_image(soup.div, 'https://example.com/search'),
            'https://cdn.example.com/phone.jpg',
        )

    def test_extracts_picture_source_srcset(self):
        soup = BeautifulSoup(
            '''
            <div>
                <picture>
                    <source srcset="//cdn.example.com/item-1x.jpg 1x, //cdn.example.com/item-2x.jpg 2x">
                </picture>
            </div>
            ''',
            'html.parser',
        )

        self.assertEqual(
            extract_product_image(soup.div, 'https://example.com/search'),
            'https://cdn.example.com/item-2x.jpg',
        )

    def test_enrich_products_uses_static_placeholder_for_missing_image(self):
        enriched = enrich_products([
            {'price': '100', 'tag': 'amazon', 'product_name': 'Test', 'a': '#', 'img': '#'}
        ])

        self.assertEqual(enriched[0]['img'], IMAGE_PLACEHOLDER)
        self.assertTrue(enriched[0]['is_static_img'])

    def test_enrich_products_preserves_static_product_image(self):
        enriched = enrich_products([
            {'price': '54', 'tag': 'blinkit', 'product_name': 'Eggs', 'a': '#', 'img': 'images/grocery/eggs.png'}
        ])

        self.assertEqual(enriched[0]['img'], 'images/grocery/eggs.png')
        self.assertTrue(enriched[0]['is_static_img'])


class GrocerySearchRecallTests(SimpleTestCase):
    def test_expands_common_grocery_query(self):
        queries = expand_search_queries('egg')

        self.assertIn('egg', queries)
        self.assertIn('eggs', queries)

    @patch('home.views.scrape_jiomart_grocery', return_value=[])
    @patch('home.views.scrape_amazon_fresh', return_value=[])
    def test_common_grocery_query_returns_supported_fallback_platforms(self, *_):
        results = collect_grocery_results('egg')
        tags = {item['tag'] for item in results}

        self.assertTrue({'blinkit', 'instamart', 'zepto', 'bigbasket', 'jiomart', 'amazonfresh'}.issubset(tags))
        self.assertEqual([int(item['price']) for item in results], sorted(int(item['price']) for item in results))

    def test_smart_category_detection(self):
        self.assertEqual(classify_search_query('milk'), CATEGORY_GROCERY)
        self.assertEqual(classify_search_query('iphone'), CATEGORY_ELECTRONICS)
        self.assertEqual(classify_search_query('iphone case'), CATEGORY_ACCESSORY)
