"""词典关系、读音及振假名的回归检查。Created by Jobs."""
import unittest
from time import perf_counter
from jobs_kanji_by_jap.catalog import Catalog
from jobs_kanji_by_jap.linguistics import ruby_parts, spoken_reading, allowed_senses


class DictionaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = Catalog()

    @classmethod
    def tearDownClass(cls):
        cls.catalog.close()

    def test_integrity_and_coverage(self):
        self.assertEqual(self.catalog.db.execute('pragma integrity_check').fetchone()[0], 'ok')
        self.assertEqual(len(self.catalog.search()), 13108)
        self.assertGreater(self.catalog.coverage['counts']['words'], 200000)

    def test_multiple_readings(self):
        readings = [r['text'] for r in self.catalog.kanji('生')['readings']]
        self.assertIn('セイ', readings)
        self.assertIn('ショウ', readings)
        self.assertIn('い.きる', readings)
        self.assertIn('なま', readings)

    def test_reading_search(self):
        self.assertIn('学', [r['literal'] for r in self.catalog.search('がくせい')])
        self.assertIn('生', [r['literal'] for r in self.catalog.search('学生')])
        self.assertEqual(len(self.catalog.search("' OR 1=1 --")), 0)

    def test_reading_restrictions(self):
        entry = {'senses': [dict(stagk=['今日'], stagr=['きょう']), dict(stagk=[], stagr=['こんにち'])]}
        self.assertEqual(len(allowed_senses(entry, '今日', 'きょう')), 1)
        self.assertEqual(len(allowed_senses(entry, '明日', 'きょう')), 0)

    def test_ruby_okurigana_and_jukujikun(self):
        self.assertEqual(ruby_parts('食べます', 'タベマス'), [('食', 'た'), ('べます', '')])
        self.assertEqual(ruby_parts('今日', 'キョウ'), [('今日', 'きょう')])
        self.assertEqual(ruby_parts('です', 'デス'), [('です', '')])
        self.assertEqual(ruby_parts('未知', '未知'), [('未知', '未识别')])
        self.assertEqual(spoken_reading('い.きる'), 'いきる')

    def test_filtered_lookup_uses_index(self):
        start = perf_counter()
        count, rows = self.catalog.words('食', '食べる')
        self.assertTrue(count and rows)
        self.assertLess(perf_counter() - start, 2.0)
        self.assertIn('forms_word', [r[1] for r in self.catalog.db.execute("PRAGMA index_list(forms)")])

    def test_pagination(self):
        total, first = self.catalog.words('生', limit=15)
        _, second = self.catalog.words('生', offset=15, limit=15)
        self.assertGreater(total, 30)
        self.assertFalse({r[0] for r in first} & {r[0] for r in second})


if __name__ == '__main__':
    unittest.main()
