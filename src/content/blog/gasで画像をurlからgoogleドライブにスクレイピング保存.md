---
title: 'GASで画像をURLからGoogleドライブにスクレイピング保存'
category: 'work'
slug: 'gasで画像をurlからgoogleドライブにスクレイピング保存'
order: 11
heroImage: '/images/gasで画像をurlからgoogleドライブにスクレイピング保存/Untitled.png'
---
※画像・商品参照元：FERFETCH　[https://www.farfetch.com/jp/](https://www.farfetch.com/jp/)

Googleスプレッドシートでは、IMAGE関数を使うことでURLを参照して画像をセル内に表示できる。

![](/images/gasで画像をurlからgoogleドライブにスクレイピング保存/Untitled.png)

ここからさらに、スプレッドシートに記載されたURLをスクレイピングし、Googleドライブにgoodsidごとにフォルダ分けして、各画像をDL保存する。

スプレッドシートの構成として、こんな風に商品ごとに画像URLが横に並んでいるとする。

![](/images/gasで画像をurlからgoogleドライブにスクレイピング保存/Untitled%201.png)

画像を収集したいフォルダのIDを確認する（画像だと1sqsuo～）

元のスプレッドシートからGASで以下のコードを叩く。

```jsx
// 各商品の画像数を取得する関数
function findLastCol(row) {
  var ss = SpreadsheetApp.getActiveSheet()
 
  // 指定の行を二次元配列に格納する
  var RowValues = ss.getRange(row, 2, 1, ss.getLastColumn()).getValues();
 
  // 二次元配列を一次元配列に変換する
  RowValues = Array.prototype.concat.apply([], RowValues);
 
  var lastCol = RowValues.filter(String).length;
 
  return lastCol;
}
 
// 商品数を取得する関数
function findLastRow(col) {
  var ss = SpreadsheetApp.getActiveSheet()
 
  // 指定の行を二次元配列に格納する
  var ColValues = ss.getRange(1, col, ss.getLastRow(), 1).getValues();
 
  // 二次元配列を一次元配列に変換する
  RowValues = Array.prototype.concat.apply([], ColValues);
 
  var lastRow = ColValues.filter(String).length;
 
  return lastRow;
}
 
 
function myFunction() {
  // 現在開いているシートを取得
  var ss = SpreadsheetApp.getActiveSheet();
  // 行(カラム名があるので2行目から)
  var rowCount = 2;
  var item;
  // 全部で何商品あるか
  var itemnum = findLastRow(1);
 
  // アイテムが無くなるまで繰り返す
  for(var j=1; j<itemnum; j++) {
    item = ss.getRange(rowCount, 1).getValue();
 
    if ( item == '') {
        break;
      }
 
    // 保存先フォルダのID
    var mainFolder  = DriveApp.getFolderById("1sqsuo～hogehoge確認したフォルダID");
 
    // 商品ごとにサブフォルダ作成
    mainFolder.createFolder(item);
 
    // 商品にいくつ画像があるか
    var imgnum = findLastCol(rowCount);
 
    for(var i=0; i<imgnum; i++) {
      // 画像URLを取得
      var imgurl = ss.getRange(rowCount, 2 + i).getValue();
 
      var response
 
      // 画像データを取得
      try {
        //成功時
        response =  UrlFetchApp.fetch(imgurl);
         var fileBlob = response.getBlob().setName(item + '_' + i);
 
        // 取得した画像をGoogle Driveにアップロード
        var file = DriveApp.createFile(fileBlob);
         
        // 作成したフォルダを見に行く
        var folders = DriveApp.getFoldersByName(item);
        while(folders.hasNext()) {
          var folder = folders.next();
          if(folder.getName() == item){
            break;
          }
        }
 
        // ルートディレクトリに画像が保存されているので画像フォルダにコピー
        file.makeCopy(file.getName(), folder);
 
        // ルートディレクトリの画像を削除
        file.setTrashed(true);
        } catch(e) {
        //エラー時
        }
    }
 
   // 次の行を見に行く
   ++rowCount;
  }
}
```

![](/images/gasで画像をurlからgoogleドライブにスクレイピング保存/Untitled%202.png)

商品ごとにフォルダが作られている。

![](/images/gasで画像をurlからgoogleドライブにスクレイピング保存/Untitled%203.png)

各フォルダには商品名_*.jpgの命名規則で、画像が保存されている。