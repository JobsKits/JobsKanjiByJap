"""打包入口及离线中文资源验证。Created by Jobs."""
from pathlib import Path
import sys
import tempfile
import json
from jobs_kanji_by_jap.app import main


def verify_chinese(output):
    from jobs_kanji_by_jap.chinese import LocalChinese, MODEL
    with tempfile.TemporaryDirectory() as directory:
        translator = LocalChinese(Path(directory) / 'test.sqlite')
        source = 'The little cat is sleeping under the table.'
        result = translator.translate([source])[source]
        assert '猫' in result and '待校对' not in result
        translator.close()
    Path(output).write_text(json.dumps({'passed': True, 'zh': result, 'model': str(MODEL)}, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--verify-chinese':
        verify_chinese(sys.argv[2])
    else:
        raise SystemExit(main())
