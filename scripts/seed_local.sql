-- Lokal Docker Postgres uchun minimal test ma'lumotlari.
-- docker exec -i logistika_db psql -U postgres -d logistika_db < scripts/seed_local.sql

INSERT INTO truck_types (name, max_weight, max_volume, is_active, created_at)
VALUES ('Gazel', 3.00, 15.00, true, NOW())
ON CONFLICT (name) DO NOTHING;

INSERT INTO users (id, full_name, username, language, role, is_active, is_banned, balance)
VALUES (7915740408, 'Local Admin', 'local_admin', 'uz', 'admin', true, false, 0)
ON CONFLICT (id) DO UPDATE SET
  role = 'admin',
  is_active = true,
  full_name = EXCLUDED.full_name;

INSERT INTO users (id, full_name, username, language, role, is_active, is_banned, balance)
VALUES (900001, 'Local Driver', 'local_driver', 'uz', 'driver', true, false, 0)
ON CONFLICT (id) DO UPDATE SET
  role = 'driver',
  is_active = true,
  full_name = EXCLUDED.full_name;

INSERT INTO drivers (
  user_id, truck_type_id, truck_number, current_city, current_region,
  is_live_location_active, rating, total_trips, total_km, cancel_count,
  on_time_percent, is_available, docs_verified, is_blocked, created_at, updated_at
)
SELECT
  900001, t.id, '01L999AA', 'Toshkent', 'Toshkent',
  false, 5.00, 0, 0, 0, 100.00, true, false, false, NOW(), NOW()
FROM truck_types t
WHERE t.name = 'Gazel'
  AND NOT EXISTS (SELECT 1 FROM drivers d WHERE d.user_id = 900001);
