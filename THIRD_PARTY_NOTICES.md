# Third-party notices — n9aBrowserResource

## 範囲と配置

本リポジトリの基本ライセンスはGPL-3.0-or-later（`LICENSE`）。以下の第三者由来データ・画像の個別ライセンスと著作権表示を保持し、それらを一律に再ライセンスしない。

`data/` は公開マスター補完・条件定義、`icons/` は採用PNGと制作資料、`palette.json` は用途別配色。アプリは起動時にmanifestと3種類のZIPを取得する。アプリの実行コード・依存ライブラリ・ゲームアカウント情報は本リポジトリに含めない。アプリ側のコード・依存ライブラリの出典は、アプリリポジトリの `THIRD_PARTY_NOTICES.md` を参照する。


本書と `licenses/THIRD_PARTY_NOTICES.md` は同一内容。ライセンス全文の参照先は以下すべてリポジトリ内の `licenses/` を基準とする。

| 対象 | 出典 | ライセンス・変更 |
| --- | --- | --- |
| `data/combat-reference.json`、`ship-experience.json`、`ship-growth.json`、`expedition-rules.json` | [ElectronicObserverEN](https://github.com/ElectronicObserverEN/ElectronicObserver)、`5b74e9ac449e892c3b64dae43fd2d75c98f544fb` | MIT。enum・装備条件・表示文言・数値レコード等を抽出・変換。`ElectronicObserver-MIT.txt`。 |
| `data/enemy-aircraft-slots.json` | [ElectronicObserver ShipParameterRecord.csv](https://github.com/andanteyk/ElectronicObserver/blob/develop/ElectronicObserver/Assets/Record/ShipParameterRecord.csv)、2026-10-07取得 | MIT。敵IDと5スロット分の搭載数に縮約。`ElectronicObserver-MIT.txt`。 |
| `data/recurring-quests.json` | [KancolleSniffer](https://bitbucket.org/kancollesniffer/kancollesniffer/src/9a4ebdea8976c84ac368f7a2197bb291f03dfe5d/KancolleSniffer/Model/)、`9a4ebdea8976c84ac368f7a2197bb291f03dfe5d` | Apache-2.0。定期任務の条件をJSONへ変換。`Apache-2.0.txt`。 |
| `data/map-edges.json`、`map-submarines.json` | [Kcanotify](https://github.com/antest1/kcanotify/tree/874e414fb2d7c3e36f35ad75766e62a6c4c79c97/app/src/main/assets)、`874e414fb2d7c3e36f35ad75766e62a6c4c79c97` | GPL-3.0-or-later。上流の `edges.json` / `map_sub.json` に対応。`NetGuard-GPL-3.0.txt`。 |
| `icons/equipment/Locked.png` | 上記ElectronicObserverEN固定版、`ElectronicObserver.Avalonia/Assets/Equipment/Locked.png` | MIT。上流と同一の採用画像。`ElectronicObserver-MIT.txt`。 |
| 装備・熟練度・情報表示画像の制作時の参照元 | 上記ElectronicObserverEN固定版のEquipment、Level、Resource、Item、Headquarters画像 | MIT。採用画像は再作成・編集・生成したものを含み、無変更コピーとは区別する。参照・翻案元のMIT帰属を保持する。各フォルダの制作記録も参照。 |

ElectronicObserverEN: Original work copyright (c) 2014 Andante; Translation work copyright (c) 2015 Ryuu Kitsune.

KancolleSniffer: Copyright (C) 2018–2019 Kazuhiro Fujieda; Copyright (C) 2021–2023 hATrayflood.

Kcanotify: Copyright (c) 2016–2026 antest1(IE10).

## プロジェクト固有の資産と廃止済み素材

`palette.json`、`data/display-definitions.json`、`data/depth-charge-icons.json`、独自の画像・制作資料は基本ライセンスの対象。第三者由来部分の個別条件は上記のとおり維持する。熟練度画像も現在は制作記録にある生成版であり、AircraftLevelTop画像の無変更コピーではない。

マテリアルデザイン風の生成画像と、Googleが提供するMaterial Iconsは別物。アプリのメニューバー用VectorDrawableは本リポジトリには含めない。`licenses/material-icons-APACHE-2.0.txt`、`BouncyCastle-LICENSE.html`等はアプリ側と共有するライセンス資料として保持しており、該当SDKや実行コードを本リポジトリで配布しているという意味ではない。

旧 `icons/original` と旧アプリ資産 `assets/userinfo` は廃止済み。採用画像は `icons/` を正本とし、アプリのassetsへ別コピーを置かない。制作資料のファイル指定はリポジトリ相対パスのみを使用する。
