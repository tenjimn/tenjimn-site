---
title: 'SQLで特定曜日始まり週単位の集計をする'
category: 'work'
slug: 'sqlで特定曜日始まり週単位の集計をする'
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

<div class="gallery-grid">
<div class="gallery-item"><p class="gallery-caption">1</p></div>
<div class="gallery-item"><p class="gallery-caption">2</p></div>
<div class="gallery-item"><p class="gallery-caption">3</p></div>
<div class="gallery-item"><p class="gallery-caption">4</p></div>
<div class="gallery-item"><p class="gallery-caption">5</p></div>
<div class="gallery-item"><p class="gallery-caption">6</p></div>
<div class="gallery-item"><p class="gallery-caption">7</p></div>
<div class="gallery-item"><p class="gallery-caption">8</p></div>
<div class="gallery-item"><p class="gallery-caption">9</p></div>
<div class="gallery-item"><p class="gallery-caption">10</p></div>
<div class="gallery-item"><p class="gallery-caption">11</p></div>
<div class="gallery-item"><p class="gallery-caption">12</p></div>
<div class="gallery-item"><p class="gallery-caption">13</p></div>
<div class="gallery-item"><p class="gallery-caption">14</p></div>
<div class="gallery-item"><p class="gallery-caption">15</p></div>
</div>

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