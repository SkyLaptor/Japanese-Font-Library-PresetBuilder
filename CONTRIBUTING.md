# 開発ガイドライン
## はじめに（必ずお読みください）
本プロジェクトへの貢献を検討いただきありがとうございます。 メンテナーの負担軽減とプロジェクトの品質維持のため、以下のルールを遵守してください。これらが守られていないプルリクエストは、内容を確認せずにクローズする場合があります。

* Issue優先: 大きな変更や機能追加を行う前に、必ずIssueで提案し合意を得てください。
* 最小PRs: 変更は可能な限り最小単位に分割してください。巨大な変更はレビュー対象外となります。
* 品質管理: ローカルでのビルドおよびテスト通過は必須条件です。

## 開発フロー
本リポジトリでは GitLab-Flow を採用しています。

1. mainブランチ: 全ての開発のベースです。
2. 作業ブランチ: `main` から作業用のブランチ(`feature/issue-番号`等)を切って作業してください。
3. マージ: `main` へのマージは、レビュー承認およびCI通過後に行われます。
4. プレリリース: 仮公開は、`main` から `pre-production` ブランチへのマージによって実行されます。
5. リリース: 公開は、`pre-production` から `production` ブランチへのマージによって実行されます。

## フォルダ構成

* assets: 生のフォントTTFやSWFといった開発に必要なリソース類を配置します。
* build: 一時ビルド時などに使用します。コミット対象外。
* data: サブセットデータなどを配置します。
* dist: 最終的な配布物を保管します。コミット対象外。
* docs: ドキュメント類を配置します。
* src: プログラムソースコードを配置します。
* tests: pytestなどのテスト用コードを配置します。

## 適用対象
* 対象ゲーム: Skyrim, SkyrimSE(SkyrimAE), SkyrimVR の英語版/日本語版 全てのバージョン。
* 対象Modマネージャー: [Vortex](https://www.nexusmods.com/about/vortex), [ModOrganizer2](https://www.nexusmods.com/about/vortex) ※公式そのままの状態でカスタムを加えていないものであること。
* Mod: [SKSE](https://skse.silverlock.org/), [SkyUI](https://www.nexusmods.com/skyrimspecialedition/mods/12604) ※フォント周りに影響を及ぼす場合はIssueで提案すること。

## 大まかな開発手順
1. リポジトリから `main` ブランチをクローン/チェックアウトします。
2. 開発ツール類、テスト環境をセットアップします。
3. コンテンツを修正し、テストを実行します。`$ uv run -m pytest`
4. `main` ブランチに対してプルリクエストを作成します。

## 開発及びテスト時に使用するツール
### Visual Studio Code (VSCode)
軽量、強力なIDEです。  
https://code.visualstudio.com/

### UV
OSを汚さずにPython実行環境を準備するために使用します。  
https://docs.astral.sh/uv/getting-started/installation/
