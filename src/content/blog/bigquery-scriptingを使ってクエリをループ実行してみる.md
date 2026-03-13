---
title: 'BigQuery Scriptingを使ってクエリをループ実行してみる'
category: 'work'
slug: 'bigquery-scriptingを使ってクエリをループ実行してみる'
---
WHERE句にある絞り込み条件について、同じクエリを流用しながら、条件を変えつつforループのように実行したい場合。

UNIONや都度テーブル作成してもいいが、Resources exceeded during query execution・・・みたいに、クエリが複雑だったりデータ数が多くて、メモリが少ないと怒られたりする場合には便利そう。

Python使わなくてもBigQueryだけで済むのは嬉しい。

例として、以下のクエリのWHERE句にあるReferenceDTの条件を、2019/12/29および2019/12/30の場合でそれぞれデータ取得して、ガッチャンコ＆格納する。

```sql
SELECT 
    data_1, data_2, date
FROM `main_table`
WHERE date = target_date
```

これをBigQuery Scriptingを使ってループさせた場合が、以下のクエリ。

```sql
-- パラメータの変数名とデータ型を指定する
DECLARE target_date DATE DEFAULT CURRENT_DATE();
DECLARE i INT64 DEFAULT 1;
DECLARE n INT64 DEFAULT 0;
 
-- パラメータに格納するデータ型を指定する
DECLARE a ARRAY<DATE>;
 
-- 繰り返すクエリに反映したいパラメータ
CREATE TEMPORARY FUNCTION target_date_1() as (date(2019, 12, 29));
CREATE TEMPORARY FUNCTION target_date_2() as (date(2019, 12, 30));
SET a = [target_date_1() , target_date_2()];
 
-- パラメータが合計何個あるか＝何回ループするかを判定
SET n =
  (
  -- 既存テーブルのカラムを参照する場合は、ここで1カラムのみ参照し、何行あるかをmax(ROW_NUMBER)で取得する
  SELECT max(ROW_NUMBER)
  FROM
    (
    SELECT dt, ROW_NUMBER() OVER() AS ROW_NUMBER
    FROM UNNEST(a) as dt
    )
  );
 
LOOP
  SET target_date =
    (
    WITH param_list AS
      (
      -- 既存テーブルのカラムを参照する場合は、ここで1カラムのみ参照
      SELECT dt, ROW_NUMBER
      FROM
        (
        SELECT dt, ROW_NUMBER() OVER() AS ROW_NUMBER
        FROM UNNEST(a) as dt
        )
      ORDER BY ROW_NUMBER
      )
    SELECT dt FROM param_list WHERE ROW_NUMBER = i
    );
 
  -- 1ループごとに結果をtempテーブルに格納する
  CREATE OR REPLACE TABLE `temp_table` AS (
 
    /*
    ループで繰り返すクエリ ～ここから～
    */
 
    
SELECT 
    data_1, data_2, date
FROM `main_table`
WHERE date = target_date
 
    /*
    ループで繰り返すクエリ ～ここまで～
    */
 
  );
 
  -- temp_tableを都度参照し、ループ1回目なら新しくテーブルを作り、2回目以降なら結果を追加する
  IF i = 1 THEN
    CREATE OR REPLACE TABLE `store_table` AS (SELECT * FROM `temp_table`);
  ELSE
    INSERT INTO `store_table` SELECT * FROM `temp_table`;
  END IF;
 
  SET i = i + 1;
  IF i > n THEN
    LEAVE;
  END IF;
END LOOP;
```