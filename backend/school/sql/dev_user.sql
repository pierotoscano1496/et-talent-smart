-- Solo dev, después de las migraciones. Parámetros proporcionados por seed_dev.
-- password_hash debe generarse con make_password de Django, nunca en texto plano.
INSERT INTO school_user
    (username, email, password, first_name, last_name, role, classroom_id,
     is_active, is_staff, is_superuser, date_joined, last_login, rfid_uid)
VALUES
    (%(email)s, %(email)s, %(password_hash)s, %(first)s, %(last)s,
     %(role)s, %(classroom_id)s, TRUE, FALSE, FALSE, %(joined)s, NULL, NULL)
ON CONFLICT (email) DO NOTHING;
