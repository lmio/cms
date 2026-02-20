begin;

alter table users
    add column last_login_timestamp timestamp,
    alter column username type varchar;

rollback; -- change this to: commit;
