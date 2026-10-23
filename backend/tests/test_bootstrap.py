import tempfile
import unittest
import zipfile
from pathlib import Path
from bootstrap import initialize


class BootstrapTests(unittest.TestCase):
    def test_fresh_download_extracts_once_and_keeps_later_data_updates(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Path(folder)
            with zipfile.ZipFile(root/'runtime-assets.zip','w') as bundle:
                bundle.writestr('backend/data/market.sqlite',b'public dataset')
                bundle.writestr('frontend/dist/index.html','<html>Player Draft</html>')
            initialize(root)
            database=root/'backend/data/market.sqlite'
            self.assertEqual(database.read_bytes(),b'public dataset')
            self.assertTrue((root/'frontend/dist/index.html').exists())
            database.write_bytes(b'updated local data')
            initialize(root)
            self.assertEqual(database.read_bytes(),b'updated local data')

    def test_archive_cannot_write_outside_runtime_directories(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Path(folder)
            with zipfile.ZipFile(root/'runtime-assets.zip','w') as bundle:
                bundle.writestr('backend/data/../../../outside.txt','invalid')
            with self.assertRaises(ValueError):
                initialize(root)


if __name__=='__main__': unittest.main()
