"""中文显示边界与离线翻译验证。Created by Jobs."""
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest
from jobs_kanji_by_jap.chinese import LocalChinese, ASSETS, pos_zh, display_translation


class ChineseTests(unittest.TestCase):
    def test_all_dictionary_parts_of_speech_are_chinese(self):
        connection = sqlite3.connect(ASSETS / 'catalog.sqlite')
        tags = {p for (data,) in connection.execute('SELECT data FROM words')
                for sense in json.loads(data)['senses'] for p in sense['pos']}
        connection.close()
        for tag in tags:
            with self.subTest(tag=tag):
                text = pos_zh(tag)
                self.assertNotIn('暂未', text)
                self.assertFalse(re.search('[a-zA-Z]', text))
        self.assertEqual(pos_zh('Ichidan verb'), '一段动词')
        self.assertEqual(pos_zh('transitive verb'), '他动词')

    def test_local_model_and_persistent_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'zh.sqlite'
            engine = LocalChinese(path)
            sentence = 'The little cat is sleeping under the table.'
            result = engine.translate([sentence])[sentence]
            self.assertRegex(result, '[猫]')
            self.assertNotIn('待校对', result)
            self.assertNotRegex(result, '[a-zA-Z]')
            engine.close()
            second = LocalChinese(path)
            self.assertEqual(second.cached(sentence), result)
            self.assertIsNone(second.model)
            second.close()

    def test_no_english_fallback(self):
        with self.assertRaises(ValueError):
            display_translation('This is not a Chinese translation.')
        with self.assertRaises(ValueError):
            display_translation('')
        self.assertEqual(display_translation('▁应该多吃水果。'), '应该多吃水果。')


if __name__ == '__main__':
    unittest.main()
