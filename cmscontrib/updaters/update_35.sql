begin;

alter table fsobjects
    alter loid type oid;

rollback; -- change this to: commit;
