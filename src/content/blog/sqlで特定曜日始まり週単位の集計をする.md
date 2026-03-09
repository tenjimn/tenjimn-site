---
title: 'SQLで特定曜日始まり週単位の集計をする'
category: 'work'
slug: 'sqlで特定曜日始まり週単位の集計をする'
order: 20
---
ISOWEEKのような週番号単位の集計ではなく、例えば水曜日〜翌火曜日までの7日間を1週間単位として集計をしたい場合。

結論、BigQueryだと以下のクエリでtrancするのが一番ラク。

```sql
DATE_TRUNC(ymd, WEEK(WEDNESDAY))
```

以降は最初に書いた備忘。

```sql
select
  ymd
-- 前水曜〜火曜まで
, DATE_SUB(ymd, INTERVAL 3 DAY) as ymd_minus_3day
, EXTRACT(DAYOFWEEK FROM DATE_SUB(ymd, INTERVAL 3 DAY)) as day_of_week_of_ymd_minus_3day
, DATE_ADD( ymd, INTERVAL 1 - EXTRACT(DAYOFWEEK FROM DATE_SUB(ymd, INTERVAL 3 DAY)) DAY ) AS week_start_date
```

わかりやすく途中集計である`ymd_minus_3day`,`day_of_week_of_ymd_minus_3day`も出力しているが、日別の元データに対して`week_start_date`でgroup byして集計すれば、特定曜日始まりで週単位の集計をすることが可能。

[出力結果](SQL%E3%81%A7%E7%89%B9%E5%AE%9A%E6%9B%9C%E6%97%A5%E5%A7%8B%E3%81%BE%E3%82%8A%E9%80%B1%E5%8D%98%E4%BD%8D%E3%81%AE%E9%9B%86%E8%A8%88%E3%82%92%E3%81%99%E3%82%8B/%E5%87%BA%E5%8A%9B%E7%B5%90%E6%9E%9C%206e7716f891594af195e1a3dda332ee35.csv)

上記の例は水曜日始まりのなので3dayになっているが、木曜日始まりなら4day、火曜日始まりなら2dayにすればよい。

軽くロジックの中身にふれると、BigQueryの

>EXTRACT(DAYOFWEEK FROM date_part)

では、日曜日始まりの数を1〜7で返す関数である。

要件として、上記例の8/25水曜日始まりの7日間について確認してみると、

- 8/25水曜日→そのままの日付がweek_start_dateに入ってほしい
- 8/26木曜日→1日前の8/25がweek_start_dateに入ってほしい
- 8/27金曜日→2日前の8/25がweek_start_dateに入ってほしい

、、、というように、木曜日ならば1日前、金曜日ならば2日前の日付を取得すれば良いことがわかる。

これらの数字をDATE_ADDやDATE_SUBで取得するために、例えば木曜日ならば3日前の月曜日の日付からEXTRACTした数である2からさらに1差し引くことで、1という値を取得する。

同様に、金曜日ならば3日前の火曜日の日付からEXTRACTした数である3からさらに1差し引くことで、2という値を取得する。

注意点として、EXTRACTしたDAYOFWEEKは1〜7の数字なので、同水曜日の場合は0を取得できるようするために、最後は絶対値として-1しているのである。

あとは取得した値について、DATE_ADDを使って元のymdから足し引きすれば、直近の水曜日の日付になる。