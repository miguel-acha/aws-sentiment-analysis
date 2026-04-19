# 🎵 Spotify Sentiment Analyzer — Guía de Implementación

> **Stack:** Python 3.12 · AWS Lambda · Spotify Web API · Amazon Comprehend · Amazon S3  
> **Reunión:** 19 Abril 2026

---

## 📁 Estructura del Proyecto

```
spotify-sentiment-analyzer/
├── src/
│   ├── spotify_client.py
│   ├── sentiment_analyzer.py
│   ├── aggregator.py
│   ├── chart_generator.py
│   ├── s3_uploader.py
│   └── lambda_handler.py
├── templates/
│   └── report.html.j2
├── tests/
│   ├── test_spotify_client.py
│   ├── test_sentiment_analyzer.py
│   ├── test_aggregator.py
│   └── test_chart_generator.py
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## ⚙️ Setup Inicial

### 1. Variables de entorno (`.env` local / Secrets Manager en prod)

```
SPOTIFY_CLIENT_ID=<tu_client_id>
SPOTIFY_CLIENT_SECRET=<tu_client_secret>
AWS_REGION=us-east-1
S3_BUCKET_NAME=spotify-sentiment-reports
```

### 2. `requirements.txt`

```
spotipy==2.23.0
boto3==1.34.0
matplotlib==3.8.0
jinja2==3.1.3
Pillow==10.2.0
```

### 3. `requirements-dev.txt`

```
pytest
pytest-mock
python-dotenv
moto[comprehend,s3,secretsmanager]
```

---

## 🔧 Módulos — Implementación Detallada

---

### `spotify_client.py` (Dev 1)

**Responsabilidad:** Autenticarse con Spotify vía Client Credentials y retornar la lista de canciones de una playlist.

**Pasos:**
1. Crear app en [Spotify Developer Portal](https://developer.spotify.com/dashboard)
2. Usar `spotipy.SpotifyClientCredentials` para autenticación
3. Llamar a `sp.playlist_tracks(playlist_id)` y paginar los resultados
4. Retornar lista de dicts `{ "track_id": str, "name": str, "artist": str, "text": str }`

> ⚠️ **Nota MVP:** Como Spotify no provee letras, el campo `text` será `"<nombre canción> <artista>"`.  
> 📌 **Fase 2:** Integrar Genius API o similar para obtener letras reales.

```python
# Estructura esperada del return
[
    {
        "track_id": "4uLU6hMCjMI75M1A2tKUQC",
        "name": "Happy",
        "artist": "Pharrell Williams",
        "text": "Happy Pharrell Williams"
    },
    ...
]
```

**Referencia:** [spotipy docs](https://spotipy.readthedocs.io/en/latest/)

---

### `sentiment_analyzer.py` (Dev 2)

**Responsabilidad:** Recibir el texto de cada canción, llamar a Amazon Comprehend y retornar el sentimiento.

**Pasos:**
1. Configurar credenciales AWS (IAM Role en Lambda, `.env` en local)
2. Para cada canción, llamar a `comprehend.detect_dominant_language(Text=text)` primero
3. Luego llamar a `comprehend.detect_sentiment(Text=text, LanguageCode=lang)`
4. Retornar `"POSITIVE"`, `"NEUTRAL"`, o `"NEGATIVE"`

> ⚠️ **Importante:** Comprehend solo soporta ciertos idiomas. Si el idioma detectado no está soportado, hacer fallback a `"NEUTRAL"`.  
> 💡 **Idiomas soportados por detect_sentiment:** en, es, fr, de, it, pt, ar, hi, ja, ko, zh, zh-TW

```python
# Estructura esperada del return
[
    {
        "track_id": "4uLU6hMCjMI75M1A2tKUQC",
        "name": "Happy",
        "artist": "Pharrell Williams",
        "sentiment": "POSITIVE",
        "scores": {
            "Positive": 0.95,
            "Neutral": 0.04,
            "Negative": 0.01,
            "Mixed": 0.00
        }
    },
    ...
]
```

**Referencia:** [Amazon Comprehend detect_sentiment](https://docs.aws.amazon.com/comprehend/latest/dg/how-sentiment.html)

---

### `aggregator.py` (Dev 3)

**Responsabilidad:** Sumar los resultados y calcular el porcentaje de canciones por sentimiento.

**Pasos:**
1. Recibir la lista de canciones analizadas
2. Contar `POSITIVE`, `NEUTRAL`, `NEGATIVE`
3. Calcular porcentajes sobre el total
4. Determinar el sentimiento dominante

```python
# Estructura esperada del return
{
    "total": 20,
    "dominant": "POSITIVE",
    "counts": { "POSITIVE": 14, "NEUTRAL": 4, "NEGATIVE": 2 },
    "percentages": { "POSITIVE": 70.0, "NEUTRAL": 20.0, "NEGATIVE": 10.0 }
}
```

---

### `chart_generator.py` (Dev 3)

**Responsabilidad:** Generar el reporte visual como HTML y PNG con tema Spotify (fondo negro `#000000`, verde `#1DB954`).

**Componentes a generar:**

#### 1. Vibe Gauge (Velocímetro)
- Usar `matplotlib` con proyección polar
- Rango: -1.0 (NEGATIVO) a +1.0 (POSITIVO)
- La aguja apunta al score dominante ponderado
- Gradiente: rojo → gris → verde

#### 2. Donut Chart
- `matplotlib.patches.Wedge` o `plt.pie()`
- Colores: POSITIVO `#1DB954`, NEUTRO `#535353`, NEGATIVO `#E85D4A`
- Fondo negro `#121212`

#### 3. Song Cards
- Generar con Jinja2 en el HTML
- Chip de color según sentimiento individual de cada canción
- Mostrar nombre + artista

#### 4. Resumen final
- Total canciones, sentimiento dominante, porcentaje dominante

**Output:**
- `report.html` — abre en browser
- `report.png` — imagen combinada para subir a S3

> ⚠️ **Riesgo conocido:** `matplotlib` no viene en el runtime default de Lambda. Subirlo como **Lambda Layer** (existe una capa pública con pandas + matplotlib lista para usar).

**Referencia:** [matplotlib dark background](https://matplotlib.org/stable/gallery/style_sheets/dark_background.html)

---

### `s3_uploader.py` (Dev 4)

**Responsabilidad:** Subir el PNG generado a S3 y retornar la URL pública.

**Pasos:**
1. Usar `boto3.client('s3')`
2. Subir con `put_object()` o `upload_file()`
3. Setear `ACL='public-read'` (o usar bucket policy)
4. Retornar la URL pública: `https://<bucket>.s3.amazonaws.com/<key>`

```python
# Estructura esperada del return
{
    "url": "https://spotify-sentiment-reports.s3.amazonaws.com/reports/playlist_abc123.png",
    "key": "reports/playlist_abc123.png"
}
```

**Referencia:** [boto3 S3 upload](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-uploading-files.html)

---

### `lambda_handler.py` (Dev 4)

**Responsabilidad:** Punto de entrada Lambda. Orquesta todos los módulos en orden.

**Flujo esperado:**

```
Event (playlist_url)
    │
    ▼
spotify_client.get_tracks(playlist_url)
    │
    ▼
sentiment_analyzer.analyze_tracks(tracks)
    │
    ▼
aggregator.aggregate(analyzed_tracks)
    │
    ▼
chart_generator.generate(analyzed_tracks, summary)  →  report.html + report.png
    │
    ▼
s3_uploader.upload(report.png)
    │
    ▼
Response { html: str, png_url: str, summary: dict }
```

**Estructura del evento de entrada:**

```json
{
    "playlist_url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
}
```

**Estructura de la respuesta:**

```json
{
    "statusCode": 200,
    "body": {
        "png_url": "https://...",
        "summary": {
            "total": 20,
            "dominant": "POSITIVE",
            "percentages": { "POSITIVE": 70.0, "NEUTRAL": 20.0, "NEGATIVE": 10.0 }
        }
    }
}
```

---

## 🏗️ Infraestructura AWS

### IAM Role para Lambda

Permisos mínimos necesarios:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        { "Effect": "Allow", "Action": ["comprehend:DetectSentiment", "comprehend:DetectDominantLanguage"], "Resource": "*" },
        { "Effect": "Allow", "Action": ["s3:PutObject", "s3:PutObjectAcl"], "Resource": "arn:aws:s3:::spotify-sentiment-reports/*" },
        { "Effect": "Allow", "Action": ["secretsmanager:GetSecretValue"], "Resource": "arn:aws:secretsmanager:*:*:secret:spotify/*" }
    ]
}
```

### Lambda Layer para matplotlib

Usar la capa pública existente o crear una:

```bash
pip install matplotlib jinja2 Pillow -t python/
zip -r matplotlib-layer.zip python/
aws lambda publish-layer-version \
    --layer-name matplotlib-layer \
    --zip-file fileb://matplotlib-layer.zip \
    --compatible-runtimes python3.12
```

### S3 Bucket

```bash
aws s3api create-bucket --bucket spotify-sentiment-reports --region us-east-1
aws s3api put-bucket-policy --bucket spotify-sentiment-reports --policy file://bucket-policy.json
```

---

## 🧪 Testing

### Por módulo

```bash
# Correr todos los tests
pytest tests/ -v

# Solo un módulo
pytest tests/test_spotify_client.py -v

# Con coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### Prueba rápida de Comprehend (Dev 2)

```python
import boto3
client = boto3.client('comprehend', region_name='us-east-1')
response = client.detect_sentiment(Text="I am so happy today!", LanguageCode="en")
print(response['Sentiment'])  # Esperado: POSITIVE
```

### Prueba rápida de Spotify (Dev 1)

```python
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
results = sp.playlist_tracks("37i9dQZF1DXcBWIGoYBM5M")
print(results['items'][0]['track']['name'])
```

---

## ⚠️ Riesgos y Soluciones

| Nivel | Riesgo | Solución |
|-------|--------|----------|
| 🔴 ALTO | Spotify no provee letras | MVP: usar `"nombre + artista"` como texto. Fase 2: Genius API |
| 🟡 MEDIO | `matplotlib` no está en Lambda | Subir como Lambda Layer |
| 🟡 MEDIO | Playlists multi-idioma | Llamar a `detect_dominant_language()` antes de `detect_sentiment()` |
| 🟢 BAJO | Costos AWS fuera del free tier | Lambda: 1M invocaciones/mes. Comprehend: 50k unidades/mes. S3: 5 GB |

---

## 📋 Checklist por Dev antes del 19 de Abril

### Dev 1 — Spotify
- [ ] Crear app en Spotify Developer Portal
- [ ] Obtener `CLIENT_ID` y `CLIENT_SECRET`
- [ ] Implementar `spotify_client.py` y probar con una playlist pública
- [ ] Leer: [Client Credentials Flow](https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow) · [spotipy docs](https://spotipy.readthedocs.io)

### Dev 2 — Comprehend
- [ ] Configurar credenciales AWS locales (`aws configure`)
- [ ] Implementar `sentiment_analyzer.py`
- [ ] Testear con textos en inglés y español
- [ ] Leer: [detect_sentiment docs](https://docs.aws.amazon.com/comprehend/latest/dg/how-sentiment.html)

### Dev 3 — Charts
- [x] Implementar `aggregator.py`
- [x] Implementar `chart_generator.py` (Gauge + Donut + Cards)
- [x] Probar output visual con datos mock
- [ ] Leer: [matplotlib dark background](https://matplotlib.org/stable/gallery/style_sheets/dark_background.html)

### Dev 4 — Lambda + S3
- [ ] Crear bucket S3 y configurar permisos
- [x] Implementar `s3_uploader.py`
- [x] Implementar `lambda_handler.py`
- [ ] Deployar Lambda y hacer prueba end-to-end
- [ ] Leer: [Lambda Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html) · [boto3 S3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-uploading-files.html)

---

## 🚀 Fases del Proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| **MVP** | Nombre + artista como texto de entrada, reporte HTML + PNG | 🔨 En progreso |
| **Fase 2** | Integrar Genius API para letras reales | ⏳ Pendiente |
| **Fase 3** | Dashboard web interactivo con historial de playlists | ⏳ Pendiente |
