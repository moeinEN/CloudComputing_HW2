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
git worktree add --detach ../cc-hw2-unlocked cd1eb0fa3792d92c47b528fb3846db8489b85aee
```

هر سه نسخه فایل `/data/queue.lock` را جداگانه باز می‌کنند. قفل، خواندن و تغییر صف را پوشش می‌دهد. `next` فایل موقت همان پوشه را با `os.replace` جایگزین می‌کند. نوبت، طول صف در لحظهٔ افزودن است و پس از برداشت ممکن است همان شماره دوباره صادر شود.
