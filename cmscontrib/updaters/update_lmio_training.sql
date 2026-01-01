begin;

alter table users
    add column last_login_timestamp timestamp;

rollback; -- change this to: commit;
