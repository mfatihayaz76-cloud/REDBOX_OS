from pathlib import Path
import hashlib
import shutil
from datetime import datetime
import sys

if len(sys.argv) != 2:
    print("KULLANIM:")
    print("python apply_patch.py patch.py")
    raise SystemExit(1)

patch_file = Path(sys.argv[1])

if not patch_file.exists():
    print("PATCH BULUNAMADI")
    raise SystemExit(1)

app = Path("app.py")

if not app.exists():
    print("app.py BULUNAMADI")
    raise SystemExit(1)

backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)

backup = backup_dir / (
    "app_before_patch_" +
    datetime.now().strftime("%Y%m%d_%H%M%S") +
    ".py"
)

shutil.copy2(app, backup)

namespace = {
    "__file__": str(patch_file),
}

exec(patch_file.read_text(encoding="utf-8"), namespace)

new_text = namespace["PATCH"](app.read_text(encoding="utf-8"))

compile(new_text, "app.py", "exec")

app.write_text(new_text, encoding="utf-8")

print("=" * 60)
print("PATCH SUCCESS")
print("BACKUP :", backup)
print("SHA256 :", hashlib.sha256(app.read_bytes()).hexdigest())
print("=" * 60)
