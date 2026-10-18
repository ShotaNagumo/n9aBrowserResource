# n9aBrowserResource

n9aブラウザの公開リソースの正本。アプリのビルド時には取得・同梱せず、アプリ起動時に公開manifestとGitHub Releasesから取得します。実行コード・ゲームアカウントの情報・個人設定・ログは含めません。

## 内容

- `data/`: 敵搭載数、海域マス、経験値・成長、戦闘参照、爆雷アイコン分類、表示分類、定期任務・遠征条件、および通常・期間限定任務の説明・宣言的な条件（`quest-catalog.json`）。
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

リポジトリの基本ライセンスはGPL-3.0-or-laterです。第三者由来部分は個別ライセンスと帰属表示を保持します。74EN由来のデータと画像の参照元はMIT、Sniffer由来の任務定義はApache-2.0、Kcanotify由来の海域情報はGPL-3.0-or-laterです。Locked.pngは独自の幾何図形から作成しています。熟練度等の採用画像は再作成・編集・生成版を含み、上流の無変更コピーとは区別します。対象ファイルと制作経緯は [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) および各iconsフォルダの制作記録を参照してください。ライセンス全文は `licenses/` に保持します。

## 公開前の確認

制作記録には採用ファイルのリポジトリ相対パスのみを記載し、端末の絶対パス・ユーザーディレクトリ・生成時の一時ファイルパスを含めません。`python scripts/check_public_paths.py` で検査します。パッケージ生成・公開スクリプトも処理開始前に同じ検査を実行します。管理用ソースZIPにも同じルールを適用します。

## 任務定義の編集

アプリが読むのは `data/quest-catalog.json` の名前付きスキーマ。任務IDをキーに、説明、tasks、formation、period、fleetIdsを記載します。tasksはkind/target/map/rank等、formationはall/any/countと艦種・艦型・改装段階等のselectorを持ちます。任意のプログラムは配信しません。

補完条件の正本は `definitions/quest-overrides.json`。上流から取得した descriptions.json、trackers.json、metadata.json を同じ入力ディレクトリへ置き、`python scripts/import_quest_catalog.py 入力ディレクトリ 固定コミットSHA` で変換します。入力の位置依存配列は変換時に解釈し、そのままアプリの公開形式にはしません。上流へのアクセスは制作時のみで、アプリから直接取得しません。

初回の変換はElectronicObserverEN/Dataの1603c0ac77fd57e7ee44f1ebc31dde84f74cd867、674任務と52件の編成補完です。既存の定期任務はrecurring-quests.jsonを引き続き使用します。未収録の達成条件・観測根拠のない初回クリアは未対応のまま扱います。

legacyCounterKeys/legacyDefinitionHashは保存カウンタの移行情報です。条件を編集した後に旧ハッシュを更新してはいけません。意味が変われば旧署名は適用されず、新しいカウンタになります。タスク、編成、艦隊指定が変わらなければ旧カウントを維持します。

変更のないパッケージは既存Releaseの版固定URLを参照できます。古いReleaseに参照が残っている間は削除しないでください。新版では変更したZIPだけを添付し、最後にmanifestを更新します。
