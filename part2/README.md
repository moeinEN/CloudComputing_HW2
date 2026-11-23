# صف نوبت آزمایشگاه

سرویس Python سه مسیر دارد. پاسخ‌ها متن UTF-8 هستند و `/join` یک بدنهٔ JSON می‌گیرد.

| درخواست | پاسخ |
| --- | --- |
| `GET /health` | `200 ok` |
| `POST /join` با بدنهٔ `{"name":"Ali"}` | `200` و طول صف پس از افزودن، یا `400` برای ورودی نامعتبر |
| `POST /next` | `200` و نام نفر اول، یا `404 empty` |

## آزمون‌ها

از ریشهٔ مخزن اجرا کنید.

```sh
cd part2
python -m pip install -r requirements-dev.txt
pytest
```

## یک نسخه از سرویس

فایل محلی `.env` را بیرون مخزن از روی `.env.example` بسازید و مثلاً `APP_PORT=8000` بگذارید. دستورهای زیر را در `part2/` اجرا کنید و `queue_env` را روی مسیر فایل محلی بگذارید.

```sh
queue_env=../../HW2_40231039/.env
docker compose --env-file "$queue_env" -p queue-single -f compose.yaml -f compose.single.yaml up -d --build app
curl -fsS http://localhost:8000/health
```

مجموعهٔ `postman/lab-queue.postman_collection.json` را وارد Postman کنید. اگر پورت را عوض کردید، مقدار `baseUrl` را تغییر دهید. بعد از چند `join` و یک `next`، یک نام در صف بگذارید و ماندگاری را بررسی کنید.

```sh
docker ps -a
docker stats --no-stream
docker volume inspect queue-single_queue-data
docker compose --env-file "$queue_env" -p queue-single exec app cat /data/queue.txt
docker compose --env-file "$queue_env" -p queue-single rm -sf app
docker compose --env-file "$queue_env" -p queue-single -f compose.yaml -f compose.single.yaml up -d --build app
docker compose --env-file "$queue_env" -p queue-single exec app cat /data/queue.txt
docker compose --env-file "$queue_env" -p queue-single down
```

`down` بدون `-v` دادهٔ آزمایش را نگه می‌دارد. برای مشاهدهٔ بازسازی image پس از تغییر کد، بعد از تغییر یک کامنت در `app/` دستور `up -d --build app` را با همان گزینه‌ها تکرار کنید.

## سه نسخه پشت nginx

```sh
docker compose --env-file "$queue_env" -p queue-locked up -d --build --scale app=3
docker compose --env-file "$queue_env" -p queue-locked ps
curl -fsS http://localhost:8000/health
python tools/concurrent_join.py --url http://localhost:8000 --drain
python tools/concurrent_join.py --url http://localhost:8000 --parallel-next
docker compose --env-file "$queue_env" -p queue-locked logs --no-log-prefix proxy | grep 'upstream='
docker compose --env-file "$queue_env" -p queue-locked down
```

برای هر آزمایش از صف خالی استفاده کنید. یک اجرای موفق هر ۲۰۰ نام را برمی‌دارد و در پایان `404 empty` می‌گیرد. اگر آزمون شکست خورد، پیش از تکرار از نام پروژهٔ تازه استفاده کنید تا volume خالی داشته باشید. سه آدرس upstream متفاوت در log درخواست‌ها رسیدن ترافیک به هر سه نسخه را نشان می‌دهد.

برای اجرای نمونهٔ قبل از قفل روی یک volume خالی، از ریشهٔ مخزن یک worktree بسازید و مراحل بالا را در `part2/` آن تکرار کنید. پروژهٔ Compose را `queue-unlocked` بنامید و فقط `--drain` را اجرا کنید.

```sh
git worktree add --detach ../cc-hw2-unlocked b40a8cba4b57253ab53327e944ccce7d861c9d6b
```

هر سه نسخه فایل `/data/queue.lock` را جداگانه باز می‌کنند. قفل، خواندن و تغییر صف را پوشش می‌دهد. `next` فایل موقت همان پوشه را با `os.replace` جایگزین می‌کند. نوبت، طول صف در لحظهٔ افزودن است و پس از برداشت ممکن است همان شماره دوباره صادر شود.

## بخش امتیازی Redis

در `part2/`، با همان `queue_env` بالا و روی صف آزمایشی خالی اجرا کنید.

```sh
docker compose --env-file "$queue_env" -p queue-redis -f compose.yaml -f compose.redis.yaml up -d --build --scale app=3
python tools/concurrent_join.py --url http://localhost:8000 --parallel-next
```

`REDIS_URL` از فایل محیطی بیرون مخزن قابل تنظیم است. آدرس پیش‌فرض `redis://db:6379/0` است و Redis پورت میزبان ندارد. هر `RPUSH` طول جدید را به‌صورت اتمیک برمی‌گرداند و `LPOP` قدیمی‌ترین نام را برمی‌دارد. ذخیره‌سازی AOF با `appendfsync everysec` در volume مستقل انجام می‌شود و خاموش‌شدن ناگهانی می‌تواند حدود یک ثانیه از تغییرات را از بین ببرد.

برای آزمایش ماندگاری، یک نام در صف بگذارید. سپس `db` را بدون حذف volume با `docker compose ... rm -sf db` و `docker compose ... up -d db` دوباره بسازید و نام را از `/next` بخوانید. در هر دو دستور همان نام پروژه و همان فایل‌های Compose را بدهید.

آزمون‌های جداگانهٔ Redis و metrics به سرویس زنده نیاز ندارند.

```sh
python -m pip install -r requirements-dev.txt -r requirements-redis.txt
pytest tests_bonus
```

## بخش امتیازی Prometheus

پروژهٔ Redis را پیش از اجرا متوقف کنید تا پورت میزبان آزاد شود.

```sh
docker compose --env-file "$queue_env" -p queue-monitor \
  -f compose.yaml -f compose.redis.yaml -f compose.monitor.yaml up -d --build --scale app=3
```

Prometheus به‌طور پیش‌فرض از `http://localhost:9090` قابل دسترسی است. روی `/targets` سه نمونهٔ app و یک exporter را بررسی کنید. Prometheus هر app را مستقیم از DNS داخلی scrape می‌کند. درخواست‌های مسیر `/metrics` در نرخ HTTP حساب نمی‌شوند.

| نمودار | PromQL |
| --- | --- |
| نرخ درخواست | `sum(rate(http_requests_total{job="app"}[1m]))` |
| علت خطا بر اساس status | `sum by (status) (rate(http_requests_total{job="app",status=~"4..\|5.."}[1m]))` |
| متوسط زمان پاسخ | `sum(rate(http_request_duration_seconds_sum{job="app"}[1m])) / sum(rate(http_request_duration_seconds_count{job="app"}[1m]))` |
| صدک ۹۵ | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="app"}[1m])))` |
| زمان عملیات Redis از نگاه برنامه | `sum by (operation) (rate(queue_db_operation_duration_seconds_sum[1m])) / sum by (operation) (rate(queue_db_operation_duration_seconds_count[1m]))` |
| طول صف مشترک | `max(queue_length{job="app"})` |
| اتصال به Redis | `redis_up{job="db"}` |
| حافظه و نرخ دستورهای Redis | `redis_memory_used_bytes{job="db"}` و `rate(redis_commands_processed_total{job="db"}[1m])` |

برای چند دقیقه، دسته‌های ۲۰۰تایی join همراه با تخلیهٔ صف اجرا کنید و چند نام نامعتبر بفرستید. با توقف موقت `db`، درخواست معتبر به `/join` یا `/next` پاسخ ۵۰۳ می‌گیرد. وقتی Redis دوباره آماده شود همین appها وصل می‌شوند. `up` دسترسی به exporter و `redis_up` دسترسی exporter به Redis را نشان می‌دهد. gauge طول صف در زمان قطعی مقدار NaN می‌دهد.
