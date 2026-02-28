# serverless-iiif-image-server-

FastAPIベースの IIIF Image API 3.0 サーバ実装です。**Level 2** 相当まで対応しています。

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
- CORS 有効化（`*`）

## セットアップ

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## 起動

ソース画像はデフォルトで `./images` 配下から読み込まれます。

```bash
uvicorn app.main:app --reload
```

環境変数 `IIIF_SOURCE_ROOT` でローカルファイルコネクタのルートを変更できます。

## コネクタ要件（データストア連携）

本プロジェクトでは、実データストア連携を分離し、`ImageSourceConnector` 契約に準拠した実装を追加する方針です。

- `fetch_image_bytes(identifier: str) -> bytes`
- 画像未存在時: `ImageNotFoundError`
- バックエンド障害時: `ConnectorError`
- `identifier` は URL デコード済み文字列として受け取る

この契約に従って、S3 / GCS / OCI / 任意ストレージ向けコネクタを追加できます。
