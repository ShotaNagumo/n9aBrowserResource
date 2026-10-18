# userinfo アイコン（最終採用版）

[比較ページ](preview.html) / [生成指示](prompts.json)

元画像は ../../original/userinfo/ に保存。生成方法は組み込み image_gen。生成指示内の旧参照パスは制作時の履歴であり、旧版画像は整理時に削除済み。アプリ組み込み用の画像は app/src/main/assets に別途保持。

`ship.png` は艦娘の所持数を表す、若い女性のシルエットへ更新済み。

`FriendlyFleet.png` は友軍艦隊用の黒色アイコンです。`ship.png` のシルエットと透明度を保ったまま、白色を黒色へ反転しています。アプリ用 assets にも同一画像を配置しています。


追加素材: `GantryCrane.png`（港湾のジブクレーン（斜めブーム・クローラーなし））、`Sparkles.png`（戦意高揚）。透過PNG。生成指示は [additional-prompts.json](additional-prompts.json)。アプリ用 assets にも同一画像を配置。表示箇所の割り当ては未実施。

ブックマーク項目用: `Bookmark1.png` / `Bookmark2.png`。共通のしおり型に番号を抜いた透過PNG。生成指示は [bookmark-prompts.json](bookmark-prompts.json)。アプリ用 assets にも同一画像を配置。将来のアイテム所持数常時表示向けの素材であり、ブックマーク機能は未実装。
