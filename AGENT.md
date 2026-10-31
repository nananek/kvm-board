# AGENT.md

このリポジトリで基板やドキュメントを更新するときの手順です。

## ツール

- KiCad 10（`kicad-cli`、Python の `pcbnew`）
- Ghostscript（`docs/` の PNG 生成に使う）
- Docker があれば `kicad/kicad:10.0` イメージで全部そろう

`scripts/kicad.sh` はリポジトリを `/work` にマウントして、コンテナ内でコマンドを実行します。
rootless Docker などで `/work` がコンテナ内で root 所有になる場合は、自動で `--user 0:0` に切り替えます。

```sh
./scripts/kicad.sh ./scripts/export_fab.sh
./scripts/kicad.sh ./scripts/gen_docs_images.sh
./scripts/kicad.sh kicad-cli pcb drc --severity-all kvm-board.kicad_pcb
```

## 生成物

| 生成物 | コマンド |
| --- | --- |
| 回路図 | `./scripts/kicad.sh python3 scripts/gen_sch.py` |
| 基板 | `./scripts/kicad.sh python3 scripts/gen_pcb.py` |
| ガーバー、ドリル、BOM、CPL | `./scripts/kicad.sh ./scripts/export_fab.sh` |
| `docs/pcb_top.png` など | `./scripts/kicad.sh ./scripts/gen_docs_images.sh` |
| 実寸確認シート | `python3 scripts/gen_print_sheet.py` |
| リポジトリ QR（URL 変更時のみ） | `python3 scripts/make_repo_qr.py`（`qrcode` が必要） |

`scripts/gen_pcb.py` で基板を作り直すと UUID が総入れ替えになり、差分が大きくなります。
シルクの座標を動かすだけのような変更では、生成スクリプトと `kvm-board.kicad_pcb` の両方に同じ値を入れて、必要なファイルだけを再生成してください。

基板裏面の QR コードは `scripts/repo_qr.txt` を読み込んで描きます。URL を変えたときだけ `scripts/make_repo_qr.py` で作り直してください。テストパッド TP1/TP2 は実装しない部品なので、BOM と CPL には入りません。

## 検証

```sh
./scripts/kicad.sh kicad-cli pcb drc --severity-all kvm-board.kicad_pcb
./scripts/kicad.sh kicad-cli sch erc --severity-all kvm-board.kicad_sch
```

どちらも 0 件を保ってください。

## コミットと PR

1. `main` から作業ブランチを切る（例: `fix/j1-a1-mark`）。
2. 生成物を再生成し、`git diff` で意図したファイルだけが変わっているか確認する。
3. DRC と ERC を実行して 0 件を確認する。
4. 署名付きでコミットする（`commit.gpgsign=true`）。
5. PR 本文は一時ファイルに書いてから作成する。コマンドラインやツールの引数に直接組み立てない。

## 基板画像の作り方

`scripts/gen_docs_images.sh` は `kicad-cli pcb export pdf` でレイヤーを書き出し、Ghostscript で PNG にしています。

- ページサイズは基板に合わせて `User 66.0 31.4` に差し替えています（PDF 出力にはページサイズの指定がないため）
- トップ: `F.Cu,F.SilkS,Edge.Cuts`
- ボトム: `B.Cu,B.SilkS,Edge.Cuts` を `--mirror`
- 配線図: `F.Cu,B.Cu,F.SilkS,Edge.Cuts`。GND ベタを見せないため、ゾーンを消した一時コピーを使います
