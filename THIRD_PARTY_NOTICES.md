# Third-party notices — n9aBrowserResource

## 範囲と配置

本リポジトリの基本ライセンスはGPL-3.0-or-later（`LICENSE`）。以下の第三者由来データ・画像の個別ライセンスと著作権表示を保持し、それらを一律に再ライセンスしない。取得先を本リポジトリへ統一しても、取り込み・変換したデータの出典は変わらない。

`data/` は公開マスター補完・条件定義、`icons/` は採用PNGと制作資料、`palette.json` は用途別配色。アプリは起動時にmanifestと3種類のZIPを取得する。アプリの実行コード・依存ライブラリ・ゲームアカウント情報は本リポジトリに含めない。アプリ側のコード・依存ライブラリの出典は、アプリリポジトリの `THIRD_PARTY_NOTICES.md` を参照する。


本書と `licenses/THIRD_PARTY_NOTICES.md` は同一内容。ライセンス全文の参照先は以下すべてリポジトリ内の `licenses/` を基準とする。

| 対象 | 出典 | ライセンス・変更 |
| --- | --- | --- |
| `data/combat-reference.json`、`ship-experience.json`、`ship-growth.json`、`expedition-rules.json` | [ElectronicObserverEN](https://github.com/ElectronicObserverEN/ElectronicObserver)、`5b74e9ac449e892c3b64dae43fd2d75c98f544fb` | MIT。enum・装備条件・表示文言・数値レコード等を抽出・変換。`ElectronicObserver-MIT.txt`。 |
| `data/enemy-aircraft-slots.json` | [ElectronicObserver ShipParameterRecord.csv](https://github.com/andanteyk/ElectronicObserver/blob/develop/ElectronicObserver/Assets/Record/ShipParameterRecord.csv)、2026-10-07取得 | MIT。敵IDと5スロット分の搭載数に縮約。`ElectronicObserver-MIT.txt`。 |
| `data/enemy-ship-hp.json` | 上記ElectronicObserverEN固定版の `ElectronicObserver.Avalonia/Assets/Record/ShipParameterRecord.csv` | MIT。敵艦IDと正かつ一意な初期耐久のみ抽出。耐久0・可変値は未収録。`ElectronicObserver-MIT.txt`。 |
| `data/recurring-quests.json` | [KancolleSniffer](https://bitbucket.org/kancollesniffer/kancollesniffer/src/9a4ebdea8976c84ac368f7a2197bb291f03dfe5d/KancolleSniffer/Model/)、`9a4ebdea8976c84ac368f7a2197bb291f03dfe5d` | Apache-2.0。定期任務の条件をJSONへ変換。`Apache-2.0.txt`。 |
| `data/map-edges.json`、`map-submarines.json` | [Kcanotify](https://github.com/antest1/kcanotify/tree/874e414fb2d7c3e36f35ad75766e62a6c4c79c97/app/src/main/assets)、`874e414fb2d7c3e36f35ad75766e62a6c4c79c97` | GPL-3.0-or-later。上流の `edges.json` / `map_sub.json` に対応。`NetGuard-GPL-3.0.txt`。 |

ElectronicObserverEN: Original work copyright (c) 2014 Andante; Translation work copyright (c) 2015 Ryuu Kitsune.

KancolleSniffer: Copyright (C) 2018–2019 Kazuhiro Fujieda; Copyright (C) 2021–2023 hATrayflood.

Kcanotify: Copyright (c) 2016–2026 antest1(IE10).

## プロジェクト固有の資産

独自制作の `icons/equipment/Locked.png`（原図 `Locked.svg`、生成処理 `scripts/render_locked_icon.ps1`）、`palette.json`、`data/display-definitions.json`、`data/depth-charge-icons.json`、独自の画像・制作資料は基本ライセンスの対象。第三者由来部分の個別条件は上記のとおり維持する。熟練度画像も現在は制作記録にある生成版であり、AircraftLevelTop画像の無変更コピーではない。

マテリアルデザイン風の生成画像を、Googleが提供するMaterial Iconsと混同しない。アプリの実行コード・依存SDKについては、アプリ側の出典一覧で管理する。

採用画像は `icons/` を正本とする。制作資料のファイル指定はリポジトリ相対パスのみを使用する。

## 通常・期間限定任務の追加配信

`data/quest-catalog.json` の説明・構造化条件・周期メタデータは [ElectronicObserverEN/Data](https://github.com/ElectronicObserverEN/Data) の固定版 `1603c0ac77fd57e7ee44f1ebc31dde84f74cd867` にある Translations/en-US/quest.json、Data/QuestTrackers.json、Data/QuestsMetadata.json を名前付きJSONへ変換したもの。出典と入力ファイルのSHA-256をcatalogのsourceに記録する。Dataリポジトリ自体のライセンス指定は確認できていないため、ElectronicObserverENのコードのMIT表記を一律に転用したり、上流由来の説明文の権利を本プロジェクトのGPL指定だけで扱ったりしない。

`definitions/quest-overrides.json` の編成補完は、従来Kotlinへ移植したKancolleSnifferのQuestFleetChecker由来条件を宣言データ化したもの。上記Apache-2.0と帰属表示を保持する。任務280の達成マップとその他の既存補正は、既存の検証済み定義から移した。ゲーム由来の文章・名称の権利を本プロジェクトが独自に付与するものではない。

## Wikiで照合した任務条件

2026-10-21に、[艦これWikiの任務表](https://wikiwiki.jp/kancolle/任務) のゲーム内部IDとの対応、指定艦・装備、海域、勝利評価、回数などの条件情報を確認し、本アプリの宣言形式・条件説明へ整理した。元のゲーム文言・名称の権利を本プロジェクトが独自に付与するものではない。確認先と取得ページのSHA-256は `definitions/master-update-provenance.json`、対応範囲は `definitions/quest-requirements-review.md` に記録する。Wiki本文の作業コピーは配信しない。
