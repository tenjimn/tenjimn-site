---
title: 'BigQueryでWHERE句で絞り込んでもデータ抽出コストが高い問題'
category: 'work'
slug: 'bigqueryでwhere句で絞り込んでもデータ抽出コストが高い問題'
order: 14
---
BigQueryで大きめの日別テーブルを参照する際に、なぜかめちゃくちゃコストが大きくなってしまったのでメモ。

結論としては、WHERE句で期間を絞り込む際に、ある記述をしてしまうと限定された範囲での抽出を行うのではなく、データ全量をなめてみてしまうのが原因。

たとえば、以下の例がNG。

```sql
-- NG
WITH
traindate as (
  SELECT
    YMD as trainYMD,
    DATE(YMD, 'Asia/Tokyo') as trainYMDdt
  FROM `calender` as calender
  WHERE 1=1
    AND DATE(calender.ymd, 'Asia/Tokyo') >= '2017-01-01'
    AND DATE(calender.ymd, 'Asia/Tokyo') <= '2017-06-30'
)

select
  ymd
, id
, content_1
, content_2

from
  `main` as main

where 1=1
  AND DATE(main.ymd, 'Asia/Tokyo') >= (select min(trainYMDdt) from traindate)
  AND DATE(main.ymd, 'Asia/Tokyo') <= (select max(trainYMDdt) from traindate)
;
```

このクエリではWITH句を使って、カレンダーテーブルから日付のユニークをサブクエリ持たせている。

データ抽出ではよくあることだが、同じ集計内容のクエリにおいて日付のみを書き換え可能にすることで、汎用性を高めるのが目的。

次にメインテーブルのWhere句において、サブクエリの日付を指定し、日付を絞り込もうとした。

しかし調査の結果、これは一度データ全量見てしまった後に、範囲を絞り込んで結果を返してくる。

なので、コストもめちゃくちゃ大きくなってしまう。

そこでチューニングした結果がこちら。

```sql
-- OK例1
CREATE TEMPORARY FUNCTION start_date() as (date(2017, 01, 01));
CREATE TEMPORARY FUNCTION end_date() as (date(2017, 06, 30));

-- OK例2
DECLARE start_date DEFAULT (
    (select min(trainYMDdt) from `中間テーブルなど`)
);
DECLARE end_date DEFAULT (
    (select max(trainYMDdt) from `中間テーブルなど`)
);

select
  ymd
, id
, content_1
, content_2

from
  `main_table`

where 1=1
  AND ymd>= start_date()
  AND ymd<= end_date()
;
```

TEMPORARY関数を定義することで、日付のみの書き換えを可能にしている。

あるいは、サブクエリではなく別テーブルから日付を呼び出す場合は、DECLAREでクエリの実行結果を変数に格納し、後から呼び出してもよい。

実際の実行時には、WHERE句にはきちんと日付がユニークで格納されるので、データ抽出の範囲を絞り込むことができ、コストもかからずに済んだ。

※仕様変更や環境によっては現象は異なるので、あくまでもメモ程度に