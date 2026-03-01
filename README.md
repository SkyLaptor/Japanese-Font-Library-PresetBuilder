# TESVFontPresetBuilder
スカイリム(無印/LE/SE/AE/VR)用のフォントプリセットを生成するためのツールです。

## 動作環境
以下のツールをインストールしてください。

* **[UV](https://docs.astral.sh/uv/)**
Pythonのパッケージ管理および実行環境です。  
PowerShell上で以下のコマンドを実行するとインストール可能です。

```powershell:uvインストール
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 使い方

### Step1. 準備
1. 本リポジトリをクローン、またはダウンロードして解凍します。
2. 使用したいフォントMODをダウンロードし、任意のフォルダに解凍しておきます。

> [!NOTE]
> 任意のフォルダにフォントMOD名のフォルダを作り、その中にフォントSWFを配置するとすっきりと管理できます。

### Step2. ツールの起動
`run.cmd` をダブルクリックして起動します。  
初回起動時は読み込みフォルダが設定されていません。画面右上の **「フォルダを開く」** を押し、[Step1. 準備](#Step1-準備)でフォントMODを置いたフォルダを指定してください。

> [!NOTE]
> 指定したフォルダ内にある全てのSWFファイルの検査が実行されます。量によっては多少時間がかかる場合があります。

### Step3. フォントのマッピング
画面左側に「読み込まれたフォント一覧」、右側に「マッピング設定（グループ単位）」が表示されます。

* **個別設定:** 左側のフォント名を選択した状態で、マップ名の隣にある `>>` を押すことで設定可能です。
* **一括適用:** 左側のリストで選択中のフォントを、ボタン一つで全グループへ一括適用することも可能です。

### Step4. プリセットの出力
マッピングが完了したら、画面右下の **「ユーザープリセットを出力」** を押し、保存先のフォルダを選択します。

指定したフォルダに `Interface` フォルダが作成され、その中に以下のファイルが生成されます。
* `fontconfig.txt`
* `fontconfig_ja.txt`
* フォントSWFファイル

これを直接ゲームの `Data` ディレクトリに配置するか、`.7z` や `.zip` に圧縮してからMOD管理ツール（[Vortex](https://www.nexusmods.com/about/vortex) / [Mod Organizer 2](https://github.com/Modorganizer2/modorganizer/releases) など）で読み込ませることでゲームに適用されます。

### Step5. 設定の保存
現在の設定内容は保存可能です。  
画面左下の **「現在のユーザープリセット設定を保存」** を押すと、次回起動時に自動で設定が読み込まれるようになります。

## フォントプレビュー機能について
本ツールには、フォントを視覚的に確認できる **プレビュー表示機能** があります。  
SWFファイル自体を編集することなく、特定のルールに従って画像ファイルを配置するだけで、UI上にサンプル画像が表示されます。

### プレビュー画像の配置ルール
以下のいずれかの条件を満たす画像ファイルが自動的に認識されます。

1. **SWFファイル名_フォント名で紐づけ**
   - SWFファイル名_フォント名と同じ名前にする。
   - 例: `fonts_apricot.swf 内の apricot_every` → `fonts_apricot_apricot_every.png`
2. **ファイル名で紐付け**
   - SWFファイルと同じ名前にする。
   - 例: `fonts_apricot.swf` → `fonts_apricot.png`
3. **フォルダ内から自動検出**
   - SWFと同じフォルダ内に、ファイル名にキーワード（`sample`,`preview`,`image`,`folder`,`directory`,`親フォルダ名`）を含む画像を置く。
   - 例: `sample.jpg`, `preview_all.png`, `myfont_sample.jpeg`

### 活用イメージ
- **配布されているフォント**: MOD紹介に貼られている画像をSWFと同じフォルダに `sample.jpg` としておいておけば、いちいちMODページを見ずとも確認できるようになります。
- **自作の確認用**: ゲーム内でのスクリーンショットを「SWF名.png」として保存しておけば、ツール上でいつでもフォントの雰囲気を確認できます。

## 言語の変更方法 / How to Change Language
本ツールは多言語対応しており、UIの表示言語を切り替えることが可能です。
The tool supports multiple languages, and you can switch the UI display language.

### Step1. コマンドラインからの指定 (Command Line)
起動時に引数を指定することで言語を変更できます。一度この方法で起動すると、設定が保存され次回以降も維持されます。  
You can specify the language using a command-line argument. Once launched this way, the setting will be saved for future sessions.

```powershell:
# 英語に設定して起動する場合 (To launch in English)
./run.cmd --lang en-us
```

### Step2. 設定ファイルからの変更 (Manual Configuration)
`settings.yml` を直接編集することでも変更可能です。  
You can also change it by manually editing `settings.yml` .

```yaml:settings.yml
lang: en-us
```

> [!NOTE]
> 翻訳へのご協力のお願い / Contributing Translations > 新たな言語の翻訳ファイルを作成いただける場合は、data/lang/<lang_code>.yml として配置してください。皆様の献身的な協力を心よりお待ちしております！  
> If you would like to provide a new translation, please place the file at data/lang/<lang_code>.yml. We welcome your contributions!