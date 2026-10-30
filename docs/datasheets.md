# データシートと基板シルクの対応

目視チェック用のリンクと、シルクの見方です。ピン番号はデータシートの番号をそのまま使っています。

## データシート

| 部品 | LCSC | パッケージ | データシート |
| --- | --- | --- | --- |
| CH9329 | C2838834 | SOP-16 | [LCSC PDF](https://www.lcsc.com/datasheet/lcsc_datasheet_2403131113_WCH-Jiangsu-Qin-Heng-CH9329_C2838834.pdf) / [秋月の英語版](https://akizukidenshi.com/goodsaffix/ch9329.pdf) |
| CH340N | C2977777 | SOP-8 | [LCSC PDF](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2403131131_WCH-Jiangsu-Qin-Heng-CH340N_C2977777.pdf) |
| USBLC6-2SC6 | C7519 | SOT-23-6 | [LCSC PDF](https://www.lcsc.com/datasheet/lcsc_datasheet_2410121836_STMicroelectronics-USBLC6-2SC6_C7519.pdf) / [ST](https://www.st.com/resource/en/datasheet/usblc6-2.pdf) |
| BAT54WS | C22629 | SOD-323 | [LCSC PDF](https://www.lcsc.com/datasheet/lcsc_datasheet_1809140116_Jiangsu-Changjing-Electronics-Technology-Co---Ltd--BAT54WS-L9_C22629.pdf) |
| TYPE-C-31-M-12 | C165948 | USB-C 16P | [LCSC PDF](https://www.lcsc.com/datasheet/lcsc_datasheet_2205251630_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf) |
| KT-0603R | C2286 | 0603 LED | [LCSC PDF](https://www.lcsc.com/datasheet/lcsc_datasheet_1810231112_Hubei-KENTO-Elec-KT-0603R_C2286.pdf) |

## シルクの見方

- `1` … ピン 1。データシートの pin 1 と同じ位置
- `K` … ダイオード/LED のカソード（データシートのカソード帯）
- `A1` … Type-C コネクタの A1 側

## 各部品の向き

| 部品 | 基板上のピン 1 / 極性 |
| --- | --- |
| U1 CH9329 | 左上。`1` マークが左上 |
| U2 CH340N | 左上。`1` マークが左上 |
| D3 USBLC6-2SC6 | 左上（I/O1）。`1` マークが左上 |
| D4 USBLC6-2SC6 | 180° 回転。ピン 1 は**右下**（フットプリントのシルク角マーク）。D3 と同じピン配置 |
| D1 BAT54WS | カソードが右（+5V 側）。`K` マークが右 |
| D2 BAT54WS | カソードが左（+5V 側）。`K` マークが左 |
| LED1 KT-0603R | カソードが右（U1 の ACT# 側）。`K` マークが右 |
| J1 / J2 | `A1` マーク側が A1。A/B の D+/D- は基板内でそれぞれ同じネット |

## ピン配置の要点

- CH9329: 7=TXD、8=RXD、12=UD+、13=UD-、15=VCC、16=V33
- CH340N: 1=UD+、2=UD-、3=GND、5=VCC、6=TXD、7=RXD、8=V3
- UART はクロス接続: U2.TXD(6) → U1.RXD(8)、U1.TXD(7) → U2.RXD(7)
- USBLC6-2SC6: 1/6=I/O1、3/4=I/O2、2=GND、5=VBUS
- Type-C: A5/B5=CC、A6/B6=D+、A7/B7=D-

詳しいピンごとの接続は [pin-review.md](pin-review.md) にあります。
