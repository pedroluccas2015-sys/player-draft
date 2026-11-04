"""After npm run build, bundle the compiled UI and public data for GitHub downloads."""
from pathlib import Path
import zipfile
import shutil

root=Path(__file__).resolve().parents[1]
files=[root/'backend/data/market.sqlite',root/'backend/data/SOURCE.json']
files+=sorted((root/'backend/data/leagues').glob('*.json'))
files+=sorted(p for p in (root/'frontend/dist').rglob('*') if p.is_file())
if not (root/'frontend/dist/index.html').exists():
    raise SystemExit('Execute npm run build em frontend antes de empacotar.')
temp=root/'runtime-assets.new.zip'
with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as bundle:
    for path in files:
        bundle.write(path,path.relative_to(root).as_posix())
temp.replace(root/'runtime-assets.zip')
print(f'Pacote de execução criado: {len(files)} arquivos, {(root/"runtime-assets.zip").stat().st_size:,} bytes.')

# Version the current compiled UI independently of the data archive.
ready=root/'frontend/ready'
if ready.exists():
    shutil.rmtree(ready)
ready.mkdir(parents=True)
for path in (root/'frontend/dist').rglob('*'):
    if path.is_file() and path.suffix in {'.html','.js','.css'}:
        destination=ready/path.relative_to(root/'frontend/dist')
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination)
