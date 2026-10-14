# Third-party components

| Component | Version | License / Source |
|---|---|---|
| Python | 3.12 | PSF; https://www.python.org/downloads/source/ |
| PySide6 / Shiboken6 / Qt | 6.8.3 | LGPL-3.0; https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/ ; https://download.qt.io/archive/qt/6.8/6.8.3/single/ |
| ZXing-C++ | 2.3.0 | Apache-2.0; https://github.com/zxing-cpp/zxing-cpp/tree/v2.3.0 |
| Pillow | 11.3.0 | HPND; https://github.com/python-pillow/Pillow/tree/11.3.0 |
| NumPy | 2.2.6 | BSD-3-Clause + bundled numerical library notices; https://github.com/numpy/numpy/tree/v2.2.6 |
| PyInstaller (build only) | 6.16.0 | GPL-2.0-or-later with distribution exception; https://github.com/pyinstaller/pyinstaller/tree/v6.16.0 |
| pytest (tests only) | 8.4.2 | MIT; https://github.com/pytest-dev/pytest/tree/8.4.2 |
| qrcode (test image generator) | 8.2 | BSD; https://github.com/lincolnloop/python-qrcode |
| OpenCV (comparison only) | 4.12.0.88 | Apache-2.0; https://github.com/opencv/opencv-python |

Qt/PySide Copyright: The Qt Company Ltd. and other contributors.
ZXing Copyright: ZXing-C++ authors and contributors, including the original ZXing authors.

Legal notices collected from installed distributions and official license texts
are under THIRD_PARTY_LICENSES. Windows builds additionally collect notices from
the installed Windows distributions. Preserve this folder, README, application
source/build instructions and DLLs when redistributing. Modified Qt/ZXing versions
must retain their corresponding license and attribution requirements.

Qt is dynamically loaded in the portable folder distribution. Library replacement,
modification and reverse engineering for debugging those modifications are permitted.
Upstream corresponding sources are linked above. Qt's licensing guidance is at
https://www.qt.io/development/open-source-lgpl-obligations .
