# Wikiからマスターを半自動更新する（Windows）

Python 3.10以上。追加ライブラリ不要。PowerShellでこのリポジトリのルートを開き、以下を実行します。`py -3` がない環境では `python` に置き換えてください。Android上では実行しません。

## 基本操作

```powershell
py -3 scripts/update_masters.py fetch
py -3 scripts/update_masters.py plan
```

`local/master-update/report.md` と `review.json` を確認します。`fetch-report.json` に取得失敗がないかも確認してください。成功・失敗件数は画面にも表示します。取得先の一部が失敗しても他のページから候補を生成できます。

候補の `after` をWiki本文と照合・修正し、反映するものだけ `approved` を `true` に変更します。**回数、勝利評価、対象海域、艦隊番号、編成・旗艦条件を必ず確認してください。自動抽出は下書きです。** ID不明や条件が未確定のまま承認しないでください。

```powershell
py -3 scripts/update_masters.py apply
py -3 -m unittest discover -s scripts/tests -v
py -3 scripts/check_public_paths.py
```

配信用ファイルの基準ハッシュが変わっていたらplanを作り直します。再planはreview.jsonを上書きするため、手作業の修正を必要に応じて別ファイルへ退避してください。ID重複は1候補に統合し、残りを未承認にします。取得だけではマスターは変わりません。applyは承認された候補だけを反映します。

反映後は隣のアプリリポジトリで回帰テストを行い、READMEの通常の公開手順へ進みます。ツールはコミット、manifest更新、Release公開を行いません。Wiki本文やローカル作業フォルダを配信ZIPに入れないでください。

## 何を更新するか

| データ | 更新内容 |
| --- | --- |
| quest-catalog.json / recurring-quests.json | 任務名・説明、既知の達成条件・編成条件・周期。既存の移行キーは維持。 |
| ship-growth.json | 味方の回避・対潜の初期／Lv99値。艦名・艦種等の基本データはアプリがゲームマスターから取得。 |
| enemy-ship-hp.json | 敵の初期耐久。複数値・不明値は上書きしない。 |
| enemy-aircraft-slots.json | 確認済みのスロット別搭載数。総搭載数からは推測しない。 |

任務の基本的な遠征成功・撃沈・演習・ボス勝利、単純な艦種隻数は候補を下書きします。複雑な既知条件はreview.jsonに入力します。新システムのトリガー、未実装の条件演算子、未知の計算式を追加するツールではありません。

単発任務のnative観測形式（period=4）を配信するには、その形式を許可するResourceValidationの修正を含むアプリが必要です。既存版のminAppVersionをそのまま流用せず、配信時に対応版を確認してください。

## 取得先とIDの設定

`definitions/master-update-sources.json` の `sources` を編集します。

```json
{
  "key": "ship-9",
  "kind": "friendly",
  "name": "吹雪",
  "shipId": 9,
  "url": "https://wikiwiki.jp/kancolle/吹雪",
  "enabled": true
}
```

`kind` は `quests`（任務表）、`friendly`（味方個艦ページ）、`enemies`（敵一覧）、`links`（艦娘索引）。同じkeyを重複させないでください。例示の吹雪は初期設定では無効です。初回は任務表・敵一覧・艦娘索引を取得します。

**Wiki任務番号D1や図鑑No.は内部IDではありません。** 任務は一意な名前か、次の明示対応で照合します。値はゲーム内部IDの整数です。新規任務で不明なIDはnullとなり、適用できません。

```json
"bindings": {
  "quests": { "quest-mission/D1": 301 },
  "ships": { "吹雪": 9 }
}
```

名前で照合できない新規任務は、公開ゲームマスター等で内部IDを確認してください。既存IDへ変更する場合はbindingsを追加してplanをやり直します。新規IDならreview.jsonの `id` に設定して承認できます。`before` や `base` を手作業で変更して整合性チェックを回避しないでください。

## 新しい味方艦のページを見つける

先に基本操作のfetchとplanで艦娘索引のリンクを取得します。公開艦マスター（`api_mst_ship` を含むJSON）を指定します。アカウントの艦所持データではありません。

```powershell
py -3 scripts/update_masters.py discover-ships --master local/public-master.json
py -3 scripts/update_masters.py --config local/master-update/ship-sources.json fetch
py -3 scripts/update_masters.py --config local/master-update/ship-sources.json plan
```

既存成長表にない内部艦IDを名前で索引に照合し、最大20ページの取得設定を追加します。追加上限は `--limit`（1～60）、既存艦も対象にするには `--all`。未解決は `ship-mapping-issues.json` に出力します。曖昧な名前は推測しません。`ship-sources.json` を確認後、今後も使う取得先を正式な設定へ取り込んでください。入力JSONの余分なフィールドは設定へ転記しません。

## ページ保存・再取得

```powershell
py -3 scripts/update_masters.py fetch --refresh
py -3 scripts/update_masters.py import-page --key en-quests --file local/saved-quests.html
py -3 scripts/update_masters.py plan
```

通常は24時間以内の正常なキャッシュを再利用します。取得失敗したページは旧キャッシュを候補へ流用しません。英語Wikiは確認時HTTP 403だったため初期設定では無効です。利用可能な環境で保存したUTF-8 HTMLまたはPukiWiki本文をimport-pageで取り込めます。アクセス制限の回避はしません。英語Wikiの実表の取得検証はできていないため、抽出結果は特に確認してください。

同一ホストの取得間隔は最低5秒（robots.txtでそれ以上の指定があれば従う）。HTTP 429／503ではその回の追加取得を中止します。取得失敗があると終了コード2です。繰り返し再試行せず時間を置いてください。失敗したページ以外で候補作成は可能です。

カスタム設定では、英語表の見出しはHP、Evasion、ASW、敵のID列はNo.／ID／API IDとして読み取ります。ページ構造が合わなければ未抽出として記録します。任務表は先頭3列がWiki番号・任務名・説明の形式を対象とします。

## レビュー時のデータ例

遠征成功を数える既知の観測形式。指定遠征なら `ids` に遠征IDを入れます。`quest.tasks` と `native` を同時に使わないでください。

```json
"after": {
  "quest": { "name": "遠征任務", "description": "全文を確認", "period": 4, "tasks": [] },
  "native": {
    "name": "遠征任務", "period": 4,
    "tasks": [{ "event": "mission", "target": 3, "ids": [], "rank": "E", "materialTypes": [], "required": 0 }]
  }
}
```

nativeの既知event: battle、practice、sink、mission、sortie、sVictory、boss、bossVictory、repair、supply、develop、build、scrapShip、improve、discardOperation、discardId、discardType、modernize。sinkのidsは艦種ID。discardIdは装備ID、discardTypeは装備カテゴリIDです。materialTypes／required等はアプリの各イベント実装と照合してください。編成条件・艦隊条件との併用は現状battle／practiceだけを許可します。

名前付きタスクはbossBattle、nodeBattle、reachNode、practice、mission、discard。例は `{"kind":"bossBattle","map":{"area":2,"number":3},"rank":"S","target":3}`。formationは既存のall／any／count／candidatesとselectorを使います。詳細はアプリ側 `doc/任務定義の配信.md`。未知のトリガー、項目や演算子は適用を拒否します。

周期は1日次・2週次・3月次・4単発・5四半期等・101～112年次開始月。年次等が下書きで未確定になった場合は確認して入力します。`legacyCounterKeys`／`legacyDefinitionHash` は変更禁止です。既存条件が未対応なら、その条件を省いて承認しないでください。

味方の `after.growth` は `[内部ID, 回避初期下限, 回避初期上限, 回避Lv99, 対潜初期下限, 対潜初期上限, 対潜Lv99]`。初期値が確定していれば上下限を同じ値にします。不明な組は `[0,9999,9999]`。敵は `after.hp` と `after.slots`（5要素）です。設定の敵sourceに `"slotCounts":{"1515":[0,0,0,0,0]}` のように確認済み値を明示することもできます。総搭載数は使わず、未確定値を0で埋めないでください。

## 中断時の復旧

```powershell
py -3 scripts/update_masters.py recover
```

applyは全候補の検証後、バックアップとジャーナルを作り、ファイルを置き換えます。通常の例外は復旧し、強制終了時は次回recoverが必要です。別の編集が加わっていたら上書きを止めます。完了した適用の取消は自動recoverの対象外なので、通常のGit差分レビューに従って戻してください。

`local/` はGit管理・ソースZIPの対象外。適用したデータと `definitions/master-update-provenance.json` のみレビュー対象にします。出典URL、取得日時、ページハッシュを記録しますが、Wiki本文は登録しません。Wiki由来情報の出典・利用条件は公開時にも確認し、リポジトリの基本ライセンスと混同しないでください。

旧 `import_quest_catalog.py` は初期変換・別入力からの再取り込み用です。Wiki更新後にそのまま実行すると内容を上書きするため、通常の更新は本ツールを使ってください。
