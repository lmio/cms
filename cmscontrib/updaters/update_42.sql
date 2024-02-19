begin;

alter table contests
    add column allow_registration boolean not null default false;
alter table contests
    alter column allow_registration drop default;

rollback; -- change this to: commit;
