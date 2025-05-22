import sys
import os
from pathlib import Path

# プロジェクトのルートディレクトリを取得
project_root = Path(__file__).parent.parent

# srcディレクトリをPythonパスに追加
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path)) 