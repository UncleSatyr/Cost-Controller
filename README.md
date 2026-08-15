
# Mini Project Cost Control System V3 Production

## Upgrade V3
- Login & password management
- Role-based access control
- Permission matrix per modul
- Approval workflow pada RAB dan transaksi utama
- Audit trail
- Edit/delete dasar untuk proyek
- Backup database
- Dashboard management
- EAC / ETC & forecast profit
- CPI / SPI
- Export Excel multi-sheet
- SQLite local database

## Login awal
Username: admin
Password: admin123

Pada login pertama admin WAJIB mengganti password.

## Menjalankan
1. Install Python 3.10+.
2. Extract folder.
3. Double-click run_app.bat.
4. Browser akan membuka aplikasi.

Database:
project_cost_control_v3.db

Backup:
folder backups/

## Catatan Production
V3 ini adalah production-oriented local prototype. Untuk deployment perusahaan/multi-user, disarankan:
- PostgreSQL/MySQL
- HTTPS + reverse proxy
- session management yang lebih kuat
- password reset via email/SSO
- approval berjenjang
- immutable audit log
- automated scheduled backup
- restore testing
- attachment/document management
- API integration ERP/accounting
- server deployment dan monitoring.
