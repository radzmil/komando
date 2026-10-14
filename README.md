# KOMANDO (asas memori bersama)

Jalankan dengan Python 3: tetapkan `KOMANDO_API_KEY` kepada nilai rawak sekurang-kurangnya 32 aksara, kemudian `python memory.py`. Secara lalai API hanya mendengar di `127.0.0.1:8765`.

`POST /memories` menerima JSON `{"client_id":"CLI-1001","source":"cline","content":"Ringkasan insiden tanpa rahsia"}`. `source` juga boleh `whatsapp`. `GET /memories?client_id=CLI-1001` membaca 30 catatan terkini. Kedua-duanya memerlukan header `Authorization: Bearer <KOMANDO_API_KEY>`.

Paparan telefon tersedia di `/` dan menggunakan kunci API yang sama (disimpan dalam sessionStorage tab telefon sahaja). Untuk akses ketika laptop ditutup: deploy folder ini sebagai servis Railway, sambungkan PostgreSQL persistent dan tetapkan `DATABASE_URL`, `KOMANDO_API_KEY` (nilai rawak sekurang-kurangnya 32 aksara), `KOMANDO_HOST=0.0.0.0`. Railway mengisi `PORT` secara automatik. Jangan deploy tanpa DATABASE_URL: SQLite pada filesystem sementara Railway boleh hilang selepas restart/deploy. Gunakan domain HTTPS Railway; jangan kongsi kunci API.

Belum disambung ke webhook WhatsApp atau Cline, Railway, GitHub atau Meta. Ini paparan memori, **bukan AI chat** lagi. Kunci API ialah akses bersama tanpa pengasingan per pengguna; jangan beri kunci kepada pengguna client. Jangan simpan token, kata laluan atau log mentah dalam memori. Nombor admin WhatsApp sahaja tidak membuktikan pemilikan permintaan API.

Semakan baca-sahaja: tetapkan `KOMANDO_CLI1001_HEALTH_URL` kepada URL HTTPS endpoint kesihatan CLI-1001 yang dipercayai. `POST /diagnose` dengan JSON `{"client_id":"CLI-1001"}` (header Bearer yang sama) memeriksa HTTP tanpa mengikuti redirect dan menyimpan hasil ke memori. Admin WhatsApp boleh hantar `/support semak`. HTTP sihat tidak membuktikan mesej WhatsApp atau dashboard berfungsi. Tiada akses Railway log/GitHub atau pembaikan automatik lagi.