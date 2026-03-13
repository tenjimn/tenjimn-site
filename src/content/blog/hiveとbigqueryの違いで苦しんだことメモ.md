---
title: 'HiveとBigQueryの違いで苦しんだことメモ'
category: 'work'
slug: 'hiveとbigqueryの違いで苦しんだことメモ'
---
最近はBigQueryでばかりクエリを書いていたので、HiveQLで書く必要性に駆られたときに、その方言の違いにだいぶ苦戦した。

なので苦労したことの備忘録。

### テキストはシングルクォーテーションで囲む

BigQueryでは特に気にしたことはなかった。

他人のクエリをコピーした場合など、"あいうえお" と 'かきくけこ' の両方が混在することなどザラ。

（それもどうかと思うけど）

```sql
select
  id
, case
    when id = 1 then "株式会社A" -- ダブルクォーテーションでもOK
    when id = 2 then '株式会社B'
  end as company_name
```

これがHiveだと、シングルクォーテーションで囲む必要があるっぽい。

```sql
select
  id
, case
    when id = 1 then '株式会社A' -- シングルクォーテーションで囲む
    when id = 2 then '株式会社B' -- シングルクォーテーションで囲む
  end as company_name
```

### サブクエリには命名が必要

よく集計で行うサブクエリを使った処理を書くと、こんな感じのエラーが返される。

`cannot recognize input near '' '' '' in subquery source hive`

調べてみると、サブクエリには命名が必須っぽい。

どういうことかというと、BigQueryの場合は以下の書き方でも一応実行できる。

```sql
SELECT
  hogehoge
, sum_hugehuge

FROM
  (
	SELECT
    hogehoge
	, sum(hugehuge) as sum_hugehuge
  )
```

これがHiveだと、以下のように参照するエイリアスが1つであっても命名が必須っぽい。

これを怠ると、上記のエラーが出て怒られる。

```sql
SELECT
  hogehoge
, sum_hugehuge

FROM
  (
	SELECT
    hogehoge
	, sum(hugehuge) as sum_hugehuge
  ) AS sub -- サブクエリに名前をつける
```

### partitionテーブルの場合はwhere句で明記する

BigQueryの場合は、分割テーブルのフィールドを明記しなくても、全体を参照して処理することができた。

どういうことかというと、例えばYMDでpartitionが切られた以下のようなtestテーブルの場合

<div class="gallery-grid">
<div class="gallery-item"><p class="gallery-caption">20200101</p></div>
<div class="gallery-item"><p class="gallery-caption">20200102</p></div>
<div class="gallery-item"><p class="gallery-caption">20200103</p></div>
</div>

以下のように特に気にせずとも、全YMDをまたいでselectすることができた

```sql
SELECT
	YMD
, hogehoge
, hugehuge

FROM
	test
```

これがHiveの場合は、どのpartitionでテーブルを参照するかを明記する必要があり、上記の記述だとエラーになるっぽい。

なので直すとしたら、

```sql
SELECT
	YMD
, hogehoge
, hugehuge

FROM
	test

WHERE
	YMD = "20200101"
```

みたいな感じだろうか。

確かに普通のカラムみたいな感じで全テーブルを参照されると、せっかく分割してる意味もない気がするので、こっちのほうが正しい使い方なのかも。

ただ一アナリストの身からすると、前者のほうが楽なシチュエーションもあるので、悩ましい。