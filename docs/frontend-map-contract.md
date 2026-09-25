# Данные для карты

Фронтенд строит карту и переключаемые слои самостоятельно. Backend не рендерит карту и
не зависит от Folium, тайлового сервиса или API карт.

## Получение домов

```http
GET /geo/houses/geojson?city=Брянск&limit=1000&offset=0
```

`city` обязателен. За один запрос возвращается не более 5000 домов. Если
`metadata.has_more=true`, следующая страница запрашивается с
`offset + metadata.returned`.

Ответ имеет формат GeoJSON `FeatureCollection`. Координаты всегда идут в порядке
`[longitude, latitude]`.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "house-uuid",
      "geometry": {"type": "Point", "coordinates": [34.37, 53.21]},
      "properties": {
        "house_id": "house-uuid",
        "formatted": "Брянск, улица Примерная, дом 1",
        "city": "Брянск",
        "street": "улица Примерная",
        "house_number": "1",
        "active_reports": 3,
        "active_incidents": 1,
        "footprint_area_m2": null,
        "size_group": null
      }
    }
  ],
  "metadata": {
    "city": "Брянск",
    "returned": 1,
    "limit": 1000,
    "offset": 0,
    "has_more": false,
    "located": 1,
    "unlocated": 0,
    "geometry_source": "HOUSE_OR_ADDRESS_POINT",
    "footprint_area_available": false,
    "median_footprint_area_m2": null
  }
}
```

## Слои

GeoJSON допускает `geometry=null`. Такие объекты остаются в выдаче, но не должны
рисоваться на карте до геокодирования. Поля `located` и `unlocated` показывают покрытие
координатами на текущей странице.

Без дополнительного контракта можно построить отдельные слои домов, активных обращений
и активных инцидентов. Интенсивность и цвет вычисляются на фронтенде из числовых полей,
поэтому пороги можно менять без обновления backend.

Backend не выдаёт синтетические контуры за настоящие. Когда ingestion начнёт сохранять
геометрию и площадь здания из проверенного источника, `footprint_area_available` станет
`true`, а `footprint_area_m2` и `size_group` позволят выделять дома площадью до медианы и
выше медианы. До этого фронтенд может показывать точечный слой или явно обозначенную
демонстрационную геометрию.
