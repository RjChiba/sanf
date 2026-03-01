# SanF

FastAPI ベースの IIIF Image API 3.0 サーバ実装です。**Level 2** 相当まで対応しています。
スタンドアロンサーバとしても、既存 FastAPI アプリに組み込むパッケージとしても利用できます。

## 実装済み機能

- `GET /iiif/{identifier}/info.json`
- `GET /iiif/{identifier}/{region}/{size}/{rotation}/{quality}.{format}`
- `GET /iiif/{identifier}` から `info.json` への 303 リダイレクト
- Level 2 の主要パラメータ
  - `region`: `full`, `square`, `x,y,w,h`, `pct:x,y,w,h`
  - `size`: `max`, `w,`, `,h`, `pct:n`, `w,h`, `!w,h`
  - `rotation`: `0`, `90`, `180`, `270`
  - `quality`: `default`
  - `format`: `jpg`, `png`
- CORS 有効化（`create_app` 使用時、デフォルト `*`）

## インストール

```bash
pip install sanf
```

## 開発セットアップ

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 起動（スタンドアロン）

ソース画像はデフォルトで `./images` 配下から読み込まれます。

```bash
uvicorn sanf.main:create_app --factory --reload
```

環境変数 `IIIF_SOURCE_ROOT` でローカルファイルコネクタのルートを変更できます。

```bash
IIIF_SOURCE_ROOT=/path/to/images uvicorn sanf.main:create_app --factory --reload
```

## パッケージとして利用する

### 公開 API

| シンボル | 用途 |
|---|---|
| `IIIFServerSettings` | 設定データクラス |
| `create_app(settings)` | スタンドアロン `FastAPI` アプリを生成 |
| `create_iiif_router(settings)` | 既存アプリに組み込む `APIRouter` を生成 |
| `ImageSourceConnector` | コネクタのプロトコル定義 |
| `LocalFileConnector` | ローカルファイル用コネクタ |
| `ConnectorError` / `ImageNotFoundError` | コネクタ例外 |

### `IIIFServerSettings`

```python
from sanf import IIIFServerSettings, LocalFileConnector
from pathlib import Path

settings = IIIFServerSettings(
    connector=LocalFileConnector(root=Path("./images")),
    cors_origins=["https://example.com"],   # デフォルト: ["*"]
    jpeg_quality=85,                         # デフォルト: 85
    max_width=4096,                          # デフォルト: None（制限なし）
    max_height=4096,                         # デフォルト: None（制限なし）
)
```

### `create_app` — スタンドアロンアプリ

CORS ミドルウェアを含む完全な `FastAPI` インスタンスを返します。

```python
from sanf import create_app, IIIFServerSettings, LocalFileConnector
from pathlib import Path

settings = IIIFServerSettings(connector=LocalFileConnector(root=Path("./images")))
app = create_app(settings)
```

### `create_iiif_router` — 既存アプリへの組み込み

CORS を含まない `APIRouter` を返します。CORS は呼び出し元アプリ側で管理してください。

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sanf import create_iiif_router, IIIFServerSettings, LocalFileConnector
from pathlib import Path

settings = IIIFServerSettings(connector=LocalFileConnector(root=Path("./images")))

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
app.include_router(create_iiif_router(settings), prefix="/iiif")
```

## コネクタ要件（データストア連携）

`ImageSourceConnector` プロトコルに準拠したクラスを実装することで、任意のストレージバックエンドを接続できます。

```python
class MyS3Connector:
    def fetch_image_bytes(self, identifier: str) -> bytes:
        # S3 などから画像バイト列を返す
        ...
```

- 画像未存在時: `ImageNotFoundError` を送出
- バックエンド障害時: `ConnectorError` を送出
- `identifier` は URL デコード済み文字列として受け取る
