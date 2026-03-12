---
title: 'BigQueryでサブクエリが多い・クエリが複雑でリソース不足時の対策'
category: 'work'
slug: 'bigqueryでサブクエリが多い・クエリが複雑でリソース不足時の対策'
order: 19
---
GoogleのBigqueryでデータ分析をしていた際に、困ったので備忘録。

“Query Failed”と表示されてクエリが実行されず、以下のエラーメッセージが表示された。

```
Error: Resources exceeded during query execution: Not enough resources for query planning - too many subqueries or query is too complex..
```

要するに、SQLのサブクエリが多すぎるか、クエリが複雑すぎてリソースが足りないために、実行できないらしい。

## <strong>問題が起きた背景</strong>

WITH句やLEFT JOINなどを含めて、サブクエリが10個くらいで作られたクエリ。

上から下までで800行ほどのSQLを実行したが、エラー。

データマートはすべてDWH上に保存済。

## <strong>解決策</strong>

色々戦ってみたが、解決策としては以下の手順で大きめの実行結果のオプションを有効化した上で、中間テーブルを生成するのが良いらしい。

なので、一旦はクエリ全体をデバッグして、中間テーブルを作成、再びそれを参照できるように、WITH句などを流用して書き換える必要がある。

またセミコロンをつければ、複数のクエリであっても同時に実行可能。

```sql
CREATE OR REPLACE TABLE
  `中間テーブル` AS (
  select hogehoge
)
;

select hugehuge
from `中間テーブル`
```

## <strong>その他試した方法</strong>

似たようなエラーがある場合の解決策として、JOINをJOIN EACHという構文に置き換える方法がある。

JOIN先？元？のデータが大きいと同じエラーが出るようだが、今回はうまくいかなかったので無視。

また、

・サブクエリをJOIN系をなるべく使わずにWITH句に入れるパターン

・逆にWITH句を使わずにJOINさせるパターン

考えつく両方を試してみた。

結論、BigQuery上の総消費リソースは改善しないために、あまり意味はないらしい。

他にも良い方法があるのかもしれないが、あくまで業務優先ということで中間テーブル作成に逃げた。