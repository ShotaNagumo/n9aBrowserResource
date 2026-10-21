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

## 敵予測の耐久補完

`data/enemy-ship-hp.json` は敵艦IDごとの初期耐久を収録する任意モジュール。ゲームマスターに正の耐久がない場合だけ、戦闘前の敵予測で使用する。正式な戦闘応答のHPには適用しない。固定版のShipParameterRecord.csvを `python scripts/import_enemy_hp.py 入力CSV 固定コミットSHA` で変換し、耐久0・初期値と最大値が異なる行は除外する。入力SHA-256は配信JSONに記録する。初回は725件。

## Wikiからの半自動マスター更新（Windows PC）

Python 3.10以上の標準ライブラリで `scripts/update_masters.py` を実行します。取得→候補生成→確認・承認→反映の順で、任務条件・味方成長値・敵HP／個別搭載数を更新します。新しいゲームシステムは対象外です。IDや曖昧な条件は推測せず、未承認データは適用しません。

実行手順・新規艦のページ登録・復旧方法は [PC用更新ツール](scripts/README_master_update.md) を参照してください。作業ファイルはGit対象外の `local/` に保存し、公開ZIPにも含めません。アプリで必要な新しい定義を配信する場合は対応アプリ版も確認してください。通常の更新には本ツールを使い、旧取り込みスクリプトで確認済みデータを上書きしないでください。

## 手入力のマスター編集GUI

`scripts/start_master_editor.cmd` をダブルクリック、または `py -3 scripts/master_editor.py` で起動します。Python 3.10以上の標準ライブラリだけで動くlocalhostのGUIです。任務の達成条件・編成条件と艦データを入力し、差分を確認して保存できます。操作方法と保存先は [手動編集GUI](scripts/README_master_editor.md) を参照してください。

## 2026-10-21の任務条件補完

詳細未収録399件のうち397件を攻略Wikiと照合し、条件説明を追加しました。191件に自動カウント、248件に編成判定を追加しています（重複あり）。全件の照合・対応表は [任務条件補完レビュー](definitions/quest-requirements-review.md) を参照してください。ID384/385は名称・説明がなく未対応です。装備・資材所持や順序などを全て判定できない任務は、条件説明とゲームの達成状態を使い、部分カウンタだけで完了扱いにしません。

`conditionsText` は確認済み詳細条件の表示用、`counterPeriod` は単発の当日内演習などの集計期間指定（1日・2週・3月）です。通常の `period` と任務の再出現可否は維持します。条件文の追加だけではカウンタの署名を変更しません。新項目に対応した次回アプリ（versionCode 195以上）を先に用意してから配信してください。パッケージ生成でも最低版を195以上に設定します。既存の公開manifest・Releaseは今回更新していません。
