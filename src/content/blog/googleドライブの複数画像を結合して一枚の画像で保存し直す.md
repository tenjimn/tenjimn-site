---
title: 'Googleドライブの複数画像を結合して一枚の画像で保存し直す'
category: 'work'
slug: 'googleドライブの複数画像を結合して一枚の画像で保存し直す'
order: 10
heroImage: '/images/googleドライブの複数画像を結合して一枚の画像で保存し直す/Untitled.png'
---
![](/images/googleドライブの複数画像を結合して一枚の画像で保存し直す/Untitled.png)

こんなふうに同じ大きさの複数画像から、

![](/images/googleドライブの複数画像を結合して一枚の画像で保存し直す/Untitled 1.png)

こんなふうに1/4ずつ結合された画像をサクッと作る方法。

![](/images/googleドライブの複数画像を結合して一枚の画像で保存し直す/Untitled 2.png)

前提として、Googleドライブには、catおよびdogにフォルダが切られており、さらに中が毛色[color]ごとに分かれているとする。

![](/images/googleドライブの複数画像を結合して一枚の画像で保存し直す/Untitled 3.png)

各フォルダにはcolor_*.jpgの命名規則で、画像が保存されている。

この状態から、cat/dogの各毛色フォルダ1～4枚保存されている画像について、colorごとに1枚の画像に結合して保存し直す。

（3枚の結合がうまくいかなかった＆面倒だったので、同じ大きさのwhite.jpgをBlogフォルダ配下に設置した）

Googleのcolaboratoryを使用してPythonで実装。

```python
# colaboratoryで実行
 
# colaboratoryでGoogleドライブのフォルダを読み込む
from google.colab import drive
drive.mount('/content/drive')
 
import os
os.listdir(path='drive/My Drive/Blog')
 
# catとdogで分けて実行する
cat_path = 'drive/My Drive/Blog/cat'
dog_path = 'drive/My Drive/Blog/dog'
 
# パスが通ってるか確認
print(cat_path)
print(dog_path)
 
# catの処理
cat_images = os.listdir(path=cat_path)
print(cat_images)
 
import cv2
import numpy as np
from IPython.display import Image,display_jpeg
 
# 毛色ごとにループ
for image in cat_images:
  path = cat_path + '/' + image
  files = os.listdir(path)
  files_list = [f for f in files if os.path.isfile(os.path.join(path, f))]
  files_num = len(files_list)
 
  # 同毛色の画像が何枚あるかで分岐
  # cv2で横結合・縦結合し、color.jpgで保存
 
  if files_num == 1:
    img = cv2.imread(path + '/' + files_list[0])
    cv2.imwrite(cat_path + '/' + image + '.jpg', img)
 
  elif files_num == 2:
    img0 = cv2.imread(path + '/' + files_list[0])
    img1 = cv2.imread(path + '/' + files_list[1])
 
    img = cv2.hconcat([img0, img1])
    cv2.imwrite(cat_path + '/' + image + '.jpg', img)
 
  # 画像が3枚の場合は白画像で代替
  elif files_num == 3:
    img0 = cv2.imread(path + '/' + files_list[0])
    img1 = cv2.imread(path + '/' + files_list[1])
    img2 = cv2.imread(path + '/' + files_list[2])
    img3 = cv2.imread('drive/My Drive/Blog/white.jpg')
    img_h1 = cv2.hconcat([img0, img1])
    img_h2 = cv2.hconcat([img2, img3])
 
    img = cv2.vconcat([img_h1, img_h2])
    cv2.imwrite(cat_path + '/' + image + '.jpg', img)
 
  else:
    img0 = cv2.imread(path + '/' + files_list[0])
    img1 = cv2.imread(path + '/' + files_list[1])
    img2 = cv2.imread(path + '/' + files_list[2])
    img3 = cv2.imread(path + '/' + files_list[3])
    img_h1 = cv2.hconcat([img0, img1])
    img_h2 = cv2.hconcat([img2, img3])
 
    img = cv2.vconcat([img_h1, img_h2])
    cv2.imwrite(cat_path + '/' + image + '.jpg', img)
 
 
# dogの処理
dog_images = os.listdir(path=dog_path)
print(dog_images)
 
def hconcat_resize_min(im_list, interpolation=cv2.INTER_CUBIC):
    h_min = min(im.shape[0] for im in im_list)
    im_list_resize = [cv2.resize(im, (int(im.shape[1] * h_min / im.shape[0]), h_min), interpolation=interpolation)
                      for im in im_list]
    return cv2.hconcat(im_list_resize)
 
for image in dog_images:
  path = dog_path + '/' + image
  files = os.listdir(path)
  files_list = [f for f in files if os.path.isfile(os.path.join(path, f))]
  files_num = len(files_list)
 
  if files_num == 1:
    img = cv2.imread(path + '/' + files_list[0])
    cv2.imwrite(dog_path + '/' + image + '.jpg', img)
 
  elif files_num == 2:
    img0 = cv2.imread(path + '/' + files_list[0])
    img1 = cv2.imread(path + '/' + files_list[1])
 
    img = cv2.hconcat([img0, img1])
    cv2.imwrite(dog_path + '/' + image + '.jpg', img)
 
  elif files_num == 3:
    img0 = cv2.imread(path + '/' + files_list[0])
    img1 = cv2.imread(path + '/' + files_list[1])
    img2 = cv2.imread(path + '/' + files_list[2])
    img3 = cv2.imread('drive/My Drive/Blog/white.jpg')
    img_h1 = cv2.hconcat([img0, img1])
    img_h2 = cv2.hconcat([img2, img3]) #白画像
 
    img = cv2.vconcat([img_h1, img_h2])
    cv2.imwrite(dog_path + '/' + image + '.jpg', img)
 
  else:
    img0 = cv2.imread(path + '/' + files_list[0])
    img1 = cv2.imread(path + '/' + files_list[1])
    img2 = cv2.imread(path + '/' + files_list[2])
    img3 = cv2.imread(path + '/' + files_list[3])
    img_h1 = cv2.hconcat([img0, img1])
    img_h2 = cv2.hconcat([img2, img3])
 
    img = cv2.vconcat([img_h1, img_h2])
    cv2.imwrite(dog_path + '/' + image + '.jpg', img)
```

実行すると、メインフォルダからcat/dog別に各毛色フォルダを見に行き、中にある画像を結合して、cat/dog内の別フォルダに保存し直す。

例として、brownのフォルダにある4枚の画像からは

![](/images/googleドライブの複数画像を結合して一枚の画像で保存し直す/Untitled 1.png)

このような1枚の画像が生成され、フォルダに格納される。