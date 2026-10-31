# ピン単位レビュー

`kvm-board.kicad_sch` のネットリストと `kvm-board.kicad_pcb` のパッドネットを直接突き合わせた結果です。ERC と DRC はどちらも 0 件、回路図と基板のネットは一致しています。

## USB Type-C（J1 / J2）

| パッド | J1 (SERIAL) | J2 (HID) |
| --- | --- | --- |
| A4, A9, B4, B9 | VBUS_SER | VBUS_HID |
| A1, A12, B1, B12, SH | GND | GND |
| A5 | CC1_SER（R1 5.1k → GND） | CC1_HID（R3 5.1k → GND） |
| B5 | CC2_SER（R2 5.1k → GND） | CC2_HID（R4 5.1k → GND） |
| A6, B6 | USB_SER_DP | USB_HID_DP |
| A7, B7 | USB_SER_DM | USB_HID_DM |
| A8, B8 | 未接続（SBU） | 未接続（SBU） |

A/B 両面の D+/D- が同じネットに落ちていることを基板側でも確認済みです。CC は各ポート 2 本とも 5.1k の Rd で、デバイス（sink）として正しく見えます。

## CH9329（U1）

| Pin | 名称 | 接続 |
| --- | --- | --- |
| 1 | ACT# | LED_ACT（LED1 のカソード） |
| 2 | MODE0 | 未接続（内蔵プルアップ） |
| 3 | MODE1 | 未接続（内蔵プルアップ） |
| 4 | CFG0 | 未接続（内蔵プルアップ） |
| 5 | CFG1 | 未接続（内蔵プルアップ） |
| 6 | RST | 未接続（内蔵プルダウン） |
| 7 | TXD | UART_9329_TX → U2 pin7 (RXD) |
| 8 | RXD | UART_9329_RX → U2 pin6 (TXD) |
| 9 | UP | 未接続（5V 動作なのでプルダウン不要） |
| 10 | DEF | 未接続（内蔵プルアップ） |
| 11 | SET | TP1 テストパッド（通常は内蔵プルアップ） |
| 12 | UD+ | USB_HID_DP → D4 pin1/6 |
| 13 | UD- | USB_HID_DM → D4 pin3/4 |
| 14 | GND | GND |
| 15 | VCC | +5V（C1 100nF、C5 10uF） |
| 16 | V33 | C4 100nF → GND |

未接続ピンはデータシートの内蔵プルアップ/プルダウンで Mode 0・プロトコルモード・9600 bps になります。SET は TP1、GND は TP2 に引き出してあり、設定変更時はこの 2 つを短絡したまま WCH の設定ツールを使います。

## CH340N（U2）

| Pin | 名称 | 接続 |
| --- | --- | --- |
| 1 | UD+ | USB_SER_DP → D3 pin1/6 |
| 2 | UD- | USB_SER_DM → D3 pin3/4 |
| 3 | GND | GND |
| 4 | RTS# | 未接続（出力） |
| 5 | VCC | +5V（C2 100nF、C5 10uF） |
| 6 | TXD | UART_9329_RX → U1 pin8 (RXD) |
| 7 | RXD | UART_9329_TX → U1 pin7 (TXD) |
| 8 | V3 | C3 100nF → GND |

5V 給電時の V3 は 0.1µF で GND に落とす仕様どおりです。UART は TXD/RXD がクロスして接続されています。

## ESD（D3 / D4 USBLC6-2SC6）

| Pin | 名称 | 接続 |
| --- | --- | --- |
| 1, 6 | I/O1 | D3: USB_SER_DP / D4: USB_HID_DM |
| 2 | GND | GND |
| 3, 4 | I/O2 | D3: USB_SER_DM / D4: USB_HID_DP |
| 5 | VBUS | 各ポートのローカル VBUS（VBUS_SER / VBUS_HID） |

ピン配置は ST のデータシート（1/6 = I/O1、3/4 = I/O2、2 = GND、5 = VBUS）と一致しています。D4 は J2 のファンアウトで D+/D- が交差しないように、I/O1 を D-、I/O2 を D+ に割り当てています（USBLC6 の 2 チャネルは電気的に同一です）。

**修正した点**: VBUS ピンをダイオード OR 後の共通 +5V から、各ポートのローカル VBUS（ダイオードの前）に変更しました。データシートの推奨どおり、ESD 電流をそのポートの VBUS と GND に逃がします。あわせて USBLC6 の近くに 100nF（C6 / C7）を追加しました。データシートにも「VBUS-GND 間に 100nF を USBLC6 の近くに置く」とあります。

ダイオード OR により 2 ポートの VBUS は分離されたままなので、片方のポートの ESD がもう片方の PC の VBUS に直接流れ込む経路はありません。

## 電源 OR（D1 / D2 BAT54WS）

| 部品 | アノード (pin2) | カソード (pin1) |
| --- | --- | --- |
| D1 | VBUS_SER | +5V |
| D2 | VBUS_HID | +5V |

SOD-323 の BAT54WS は pin1 = カソードです。基板のフットプリント（D_SOD-323 の pad1 = カソード）と一致しています。負荷は CH9329 11mA + CH340N + LED でおよそ 20mA、Vf 0.3V 程度なので損失は 6mW 程度です。200mA 定格に対して余裕があります。

## パスコン

| 部品 | 接続 | 配置 |
| --- | --- | --- |
| C1 100nF | +5V / GND | U1 VCC の近く |
| C2 100nF | +5V / GND | U2 VCC の近く |
| C3 100nF | V3_340 / GND | U2 V3 の近く |
| C4 100nF | V33 / GND | U1 V33 の近く |
| C5 10uF | +5V / GND | +5V レールのバルク |
| C6 100nF | VBUS_SER / GND | D3 の近く（ESD 用） |
| C7 100nF | VBUS_HID / GND | D4 の近く（ESD 用） |

## 残っている注意点

- 2 台の PC の GND は USB ケーブル経由で共通になります。VBUS はダイオードで分離していますが、GND は分離できません。これは元の MR-CH9329EMU-USB と同じ構成です。別系統の電源につながった PC 同士で使う場合は、USB アイソレータや同一電源タップの使用を検討してください。
- Type-C コネクタのシェル固定タブは THT 形状です。JLCPCB の SMT 実装部品リストには含まれていますが、実装方法が気になる場合は完全 SMD のレセプタクルに交換できます。
- Type-C の VBUS パッドには、パッドの外側に 0.5/0.3mm のビアを置いて B.Cu で引き回しています（各コネクタ 2 個）。via-in-pad ではありません。
- CH9329 の設定変更（VID/PID、ボーレートなど）は SET ピンを GND に落とす必要があります。基板上では TP1 (SET) と TP2 (GND) を短絡してください。
