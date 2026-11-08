import sys
from pathlib import Path

# Testlerin 'src' paketini bulabilmesi için proje kökünü yola ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
