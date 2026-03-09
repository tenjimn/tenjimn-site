---
title: 'BigQueryでゼロパディングする'
category: 'work'
slug: 'bigqueryでゼロパディングする'
order: 18
---
ゼロパディング、つまり

- ”12”のような文字列→”0012”
- ”123”のような文字列→”0123”

といったように、先頭から指定文字数を担保した上で、0埋めをしたい場合。

結論、`lpad`を使う。

```sql
select lpad("12", 4, '0')
union all
select lpad("123", 4, '0')
union all
select lpad("1234", 4, '0')

-- 実行結果
0012
0123
1234
```

ちなみにlpadのlはleftのlの模様で、rにすると以下の実行結果になる。

```sql
select rpad("12", 4, '0')
union all
select rpad("123", 4, '0')
union all
select rpad("1234", 4, '0')

-- 実行結果
1200
1230
1234
```