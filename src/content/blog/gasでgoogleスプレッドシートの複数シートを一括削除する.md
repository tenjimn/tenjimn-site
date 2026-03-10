---
title: 'GASでGoogleスプレッドシートの複数シートを一括削除する'
category: 'work'
slug: 'gasでgoogleスプレッドシートの複数シートを一括削除する'
order: 12
heroImage: '/images/gasでgoogleスプレッドシートの複数シートを一括削除する/Untitled.png'
---
GASを用いる。

ここでは試しに、以下のようなシート1〜5まで存在するスプレッドシートについて、一括で2〜5を削除してみる。

上部メニューの拡張機能→Apps Scriptから、GASの編集エディタを起動する。

![Untitled](/images/gasでgoogleスプレッドシートの複数シートを一括削除する/Untitled.png)

以下のコードを（必要に応じて「削除するシート名」「削除する合計シート数」を改変しながら）コピペし、実行ボタンを押す。

```jsx
function deleteSheets() {
  // 現在アクティブなスプレッドシートを取得
  var ss_active_all = SpreadsheetApp.getActiveSpreadsheet();
  var i = 0;
 
  // 削除するシート名
  var array=["シート2","シート3","シート4","シート5"];
  // 削除する合計シート数
  const sheet_num = 4;
 
  for(i; i<=sheet_num-1; i++) {
    var delete_sheet_name = array[i];
    // そのスプレッドシートのシートを取得
    var delete_sheet = ss_active_all.getSheetByName(delete_sheet_name);
    // そのシートを削除
    ss_active_all.deleteSheet(delete_sheet);
  }
}
```

![Untitled](/images/gasでgoogleスプレッドシートの複数シートを一括削除する/Untitled%201.png)

初回は承認が必要だと言われるが、気にせずクリック。

![Untitled](/images/gasでgoogleスプレッドシートの複数シートを一括削除する/Untitled%202.png)

成功すると、「削除するシート名」で指定したシートが一括削除できる。

（同時に200シートくらいの一括削除は動作確認済）

before

![Untitled](/images/gasでgoogleスプレッドシートの複数シートを一括削除する/Untitled%203.png)

after

![Untitled](/images/gasでgoogleスプレッドシートの複数シートを一括削除する/Untitled%204.png)