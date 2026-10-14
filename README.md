# QR Screen Reader 1.0.4（Windows実機検証前の実装版）

画面・クリップボード・画像ファイルからQRコードを読み取るローカルアプリです。
Python 3.12 x64 / Windows 10・11 x64を対象にしています。Windows実機では未検証です。

## まず起動するには

このZIPにはWindows用exeは入っていません。開発環境がLinuxのため、Windows上でビルドしてください。PyInstallerはWindows用アプリをWindows上で作成する方式です。

1. ZIPを**すべて展開**します。
2. Windowsに無料のPython 3.12（64bit）をインストールします。Python Launcher（`py`）も有効にします。
3. `build_windows.bat` をダブルクリックします。初回の依存取得にはインターネット接続が必要です。費用・アカウント・APIキーは不要です。
4. 「Build succeeded」が出たら、`dist/QRScreenReader/QRScreenReader.exe` を起動します。
5. 配布する場合は **QRScreenReaderフォルダ全体** を渡してください。exeだけを取り出すと動きません。ビルド後の利用側ではPythonのインストール不要です。

管理者権限は原則不要です。フォルダは自分が書き込める場所に展開してください。
ビルドが失敗した場合は表示されたエラーを確認してください。batはエラー時に閉じず停止します。
ソースで起動する場合は、ビルドで作った環境から `start_windows.bat` を使えます。

## 操作

- アプリを起動したまま `Ctrl + Shift + Q`：画面全体を静止画として取得し、暗い選択画面を表示。QRを白い余白ごとドラッグすると解析します。`Esc` でキャンセル。
- 「画面から読み取り」：ショートカットと同じ操作。
- 「クリップボード」：スクリーンショット等の画像を解析。読み取りだけでは内容を上書きしません。
- 「画像ファイル」：PNG/JPEG/BMP/WebPを選択。日本語パスに対応。
- 「コピー」：原文をコピーします。CR/LFや制御文字も原文のままコピーします。
- 「URLを開く」：HTTP/HTTPSかつ検証済み形式のURLに限り有効。確認ダイアログで実際のURLを見て「Yes」を押したときだけ既定ブラウザで開きます。
- 「再読み取り」：直前と同じ読み取り方法を開始します。画像ファイルでは選択画面が再び開きます。

ウィンドウを最小化してもホットキーは使えます。×で閉じると終了し、ホットキーも解除されます。自動起動・トレイ常駐はありません。
ホットキー競合時は画面上に通知し、ボタン操作を継続利用できます。

## プライバシー

アプリの解析コードはネットワーク接続、履歴保存、画像保存、QR内容のログ記録を行いません。
画面は選択開始時だけ取得し、常時監視はしません。画像は選択・解析後に解放します。
結果は次の読み取りまたは終了までメモリ上に残ります。コピーした情報はWindowsのクリップボードに残ります。
OS側のクリップボード履歴・同期が有効な場合はOSの設定に従います。
URLを開く操作はブラウザによる通常のネットワーク通信を伴います。

## 構成と理由

- PySide6 6.8.3：GUIとクリップボード。QtCore/QtGui/QtWidgetsを利用。
- ZXing-C++ 2.3.0：QR復号。原始バイトを取得でき、今回の比較では制御文字の復元でOpenCVより正確でした。
- Pillow 11.3.0 / NumPy 2.2.6：画像読み込みと変換。
- Windows API：RegisterHotKey、PMv2 DPI awareness、GDIキャプチャ、モニター物理座標。
- PyInstaller 6.16.0：Windows上でPython込みのportableフォルダを作成。
- OpenCV 4.12.0.88：比較用のみ。実行時の依存には含めません。

通常は原画像で復号し、失敗した場合だけ余白追加・グレースケール・コントラスト調整・拡大を試します。
解析とファイル読み込みは別スレッドで行います。範囲選択時の1回のキャプチャはGUI側で行います。
文字列はZXingのPlainモードで復元し、原始バイトへの厳密な再変換を確認します。
復元できない・置換文字を含む・不明なバイナリデータの場合は成功扱いにしません。
URL中の空白・制御文字・認証情報・不正なホスト/ポート・危険なスキーム等は開く対象にしません。

## 開発・テスト

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python generate_samples.py
.venv\Scripts\python compare_decoders.py
```

`TEST_RESULTS.md` に実施済み／未検証の区別、`KNOWN_ISSUES.md` に制限を記載しています。
`test_images/expected.json` が期待する文字列です。
`decoder_comparison.json` は比較時の実測値です。全画像・全環境に対する認識率ではありません。

## ライセンス・参照元

アプリソースはMIT Licenseです。依存ライブラリはそれぞれのライセンスに従います。
PySide6/QtはLGPLv3、ZXingはApache-2.0、PillowはHPND、NumPyはBSD系です。
exeを単一ファイル化せず、Qt DLLを同梱するフォルダ形式にしています。ソースとビルド手順を同梱し、ライブラリ差し替え・デバッグのための改変を禁止しません。
`THIRD_PARTY_LICENSES` と `THIRD_PARTY.md` を参照してください。Windowsビルド時も同梱パッケージの法的通知を収集します。

公式資料：
- https://github.com/zxing-cpp/zxing-cpp/tree/v2.3.0
- https://github.com/zxing-cpp/zxing-cpp/blob/v2.3.0/wrappers/python/zxing.cpp
- https://doc.qt.io/qtforpython-6/
- https://www.qt.io/development/open-source-lgpl-obligations
- https://www.pyinstaller.org/
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey
- https://learn.microsoft.com/en-us/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows

## 1.0.1 修正

- 選択開始のタイマーをMainウィンドウ所有に変更。
- 選択中に最後の通常ウィンドウが非表示になってもアプリを終了しない設定に変更し、×による終了は明示処理。
- Qt/Windowsのモニター名の表記差を正規化。
- キャプチャ・モニター取得・選択画面生成／表示のどこで失敗したかダイアログ表示。QR画像・内容は保存しない。
- Windows上の「ボタンで隠れるだけ」の原因は未確定。修正後のWindows実機動作は未検証。

更新時：起動中のアプリを終了し、修正版ZIPを元のフォルダへ展開してファイルを上書きし、build_windows.batで再ビルドしてください。既存の.venvは再利用されます。旧exeを開かず、生成したdist/QRScreenReader/QRScreenReader.exeを起動します。タイトルに1.0.4と表示されます。

## 1.0.2 修正

ユーザーWindows実機で「QtとWindowsのモニター名を対応付けられません」を確認。モニター名照合を廃止し、Qtで画面へ配置した非表示ウィンドウのネイティブHWNDからMonitorFromWindow/GetMonitorInfoWで物理矩形を取得します。混在倍率の論理座標を物理座標の原点へ直接換算しません。重複モニターへの配置は安全に拒否します。

実機のエラー箇所は確認できましたが、修正版のWindows動作は未検証です。再ビルドして確認してください。
公式API資料：https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-monitorfromwindow

## 1.0.3 修正

1.0.2の「異なる画面が同じモニターへ配置されました」をユーザー画像で確認。QtのQScreenの位置決めを廃止しました。WindowsのEnumDisplayMonitorsで物理矩形を列挙し、非表示作成時・表示後の両方でSetWindowPosを使い直接配置します。GetWindowRectで指定矩形と一致することを確認します。画像の切り出し・描画・カーソルの基準は同じWindows物理座標です。

左側モニターを含む2画面配置の模擬テストを追加し38件成功。修正版のWindows実機動作は未検証です。

## 1.0.4 専用アイコン

青いQRモチーフ＋水色の読み取り枠を作成し、exeとQtアプリのアイコンに設定。装飾用で、読取用のQRではありません。assetsにPNGと7サイズ入りICOを同梱。更新後は再ビルドが必要です。Windowsのアイコンキャッシュが古い場合はショートカットを作り直してください。画面選択のコードは1.0.3と同じです。
