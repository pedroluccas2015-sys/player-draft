"""Unpack bundled public data and the compiled UI on the first local run."""
from pathlib import Path
import hashlib
import shutil
import zipfile


def initialize(root=None):
    root=Path(root or Path(__file__).resolve().parents[1]).resolve()
    archive=root/'runtime-assets.zip'
    if not archive.exists():
        return
    marker=root/'backend'/'.runtime-assets-ready'
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    required=[root/'backend/data/market.sqlite',root/'frontend/dist/index.html']
    if marker.exists() and marker.read_text(encoding='ascii')==digest and all(p.exists() for p in required):
        return
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            target=(root/entry.filename).resolve()
            if not target.is_relative_to(root) or not entry.filename.startswith(('backend/data/','frontend/dist/')):
                raise ValueError('Arquivo de execução contém um caminho não permitido.')
        for entry in bundle.infolist():
            if entry.is_dir():
                continue
            target=root/entry.filename
            target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_name(target.name+'.extracting')
            with bundle.open(entry) as source,temp.open('wb') as destination:
                shutil.copyfileobj(source,destination)
            temp.replace(target)
    marker.parent.mkdir(parents=True,exist_ok=True)
    marker.write_text(digest,encoding='ascii')
