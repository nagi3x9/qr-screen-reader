"""Copy installed distributions' upstream legal notices before distribution."""
from importlib.metadata import distributions
from pathlib import Path
import shutil
out=Path('THIRD_PARTY_LICENSES'); out.mkdir(exist_ok=True)
for dist in distributions():
    name=dist.metadata['Name']
    if name.lower().replace('_','-') not in {'pyside6','pyside6-essentials','pyside6-addons','shiboken6','zxing-cpp','pillow','numpy'}:
        continue
    for file in dist.files or []:
        if any(part.lower().startswith(('license','licence','copying','notice')) for part in file.parts):
            source=Path(dist.locate_file(file))
            if source.is_file():
                dest=out/name/str(file); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,dest)
