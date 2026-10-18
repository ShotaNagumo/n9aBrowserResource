# n9aBrowserResource

n9aブラウザの公開リソースの正本。アプリのビルド時には取得・同梱せず、アプリ起動時に公開manifestとGitHub Releasesから取得します。実行コード・ゲームアカウントの情報・個人設定・ログは含めません。

## 内容

- `data/`: 敵搭載数、海域マス、経験値・成長、戦闘参照、爆雷アイコン分類、表示分類、定期任務・遠征条件。
- `icons/`: 採用済みの装備・熟練度・情報・ダッシュボード・交戦形態PNG。制作資料とプレビューも管理します。originalは廃止済みです。
- `palette.json`: 用途別キーによる唯一の配色定義。色を変更してもキーは維持してください。
- `manifest.json`: 公開中の一式の版、対応アプリ、各ZIPと各ファイルのサイズ・SHA-256。
- `scripts/package.py`: Release添付ZIPとmanifestの生成（Python標準ライブラリのみ）。
- `licenses/` / `THIRD_PARTY_NOTICES.md`: 出典とライセンス。

## 更新・公開

1. develop上で対象ファイルを修正します。定義の形式・対応する条件型を変える場合は、先にアプリ側の対応を確認してください。計算処理や任意のコードは配信できません。
2. `python scripts/package.py 2026.10.18.2` のように、未使用の版番号で生成します。
3. 隣のアプリリポジトリで回帰テストを実行します。`-PpublicResourcesDir=このリポジトリの絶対パス` で配置を指定できます。生成される `test-runtime` はオフラインの取得テスト用です。
4. `dist/resources-版番号/` の `master.zip`、`icons.zip`、`palette.zip` を、同名のGitHub Releaseへ登録します。
5. ZIPの公開確認後、最後に新しい `manifest.json` をdevelopへコミット・pushします。manifestがZIPに先行しないようにしてください。公開済みの版は上書きせず、新版を作ります。

アプリは変更されていないZIPを再取得しません。現在版の破損時には前回正常版へ戻ります。初回は取得が必須で、失敗した場合は再試行画面になります。保存済み版がある場合、更新確認失敗時にも使用できます。

`dist` と `test-runtime` はGit管理しません。プレビュー: [icons](icons/preview.html)。

## ライセンス

リポジトリの基本ライセンスはGPL-3.0-or-laterです。74EN由来の数値レコード・熟練度等はMIT、Sniffer由来の任務定義はApache-2.0、Kcanotify由来の海域情報はGPL-3.0-or-laterです。各データの出典・帰属表示を保持してください。アプリ固有のアイコンの制作情報は各iconsフォルダにあります。

## 公開前の確認

制作記録には採用ファイルのリポジトリ相対パスのみを記載し、端末の絶対パス・ユーザーディレクトリ・生成時の一時ファイルパスを含めません。`python scripts/check_public_paths.py` で検査します。パッケージ生成・公開スクリプトも処理開始前に同じ検査を実行します。管理用ソースZIPにも同じルールを適用します。
