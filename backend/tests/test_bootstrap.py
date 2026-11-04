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

    def test_ready_ui_overrides_old_archive_and_existing_marker(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Path(folder)
            with zipfile.ZipFile(root/'runtime-assets.zip','w') as bundle:
                bundle.writestr('backend/data/market.sqlite',b'dataset')
                bundle.writestr('frontend/dist/index.html','old name-only radar')
            initialize(root)
            ready=root/'frontend/ready'
            (ready/'assets').mkdir(parents=True)
            (ready/'index.html').write_text('new club-specific radar')
            (ready/'assets/radar.js').write_text('/api/radar/player')
            initialize(root)
            self.assertEqual((root/'frontend/dist/index.html').read_text(),'new club-specific radar')
            self.assertEqual((root/'frontend/dist/assets/radar.js').read_text(),'/api/radar/player')
            (ready/'index.html').write_text('next version')
            initialize(root)
            self.assertEqual((root/'frontend/dist/index.html').read_text(),'next version')


if __name__=='__main__': unittest.main()
